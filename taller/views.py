from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.db.models import Sum, Count, F, Q
from django.db.models.functions import TruncMonth
from .forms import OrdenTrabajoForm, CitaForm
from clientes.models import Bicicleta
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from inventario.models import ServicioCatalogo, ItemInventario, Proveedor
from .models import DetalleOrdenServicio, DetalleOrdenPieza, Pago, Cita, CargoOrden, OrdenTrabajo, Evidencia
from .forms import EmpleadoForm, EvidenciaForm
from django.db import transaction
from django.urls import reverse
import urllib.parse
from django.utils import timezone
from datetime import timedelta
import json
from .decorators import admin_requerido
from core.decorators import modulo_requerido, roles_permitidos
from django.contrib.auth import get_user_model
from django.shortcuts import redirect


Usuario = get_user_model()


@login_required
def asignar_tecnico(request, pk):
    """HTMX: Asigna un mecánico a la orden de forma silenciosa"""
    if request.method == 'POST':
        orden = get_object_or_404(OrdenTrabajo, id=pk, sucursal=request.user.sucursal)
        tecnico_id = request.POST.get('tecnico_id')

        if tecnico_id:
            # Buscamos al mecánico asegurándonos que sea de la misma sucursal
            tecnico = get_object_or_404(Usuario, id=tecnico_id, sucursal=request.user.sucursal)
            orden.tecnico = tecnico
        else:
            # Si seleccionan "-- Sin asignar --"
            orden.tecnico = None

        orden.save()

        # Devolvemos un 200 OK vacío. HTMX no reemplazará nada en la pantalla
        return HttpResponse(status=200)

    return HttpResponse(status=400)

@login_required
def tablero_kanban(request):
    """
    Muestra el tablero Kanban con las órdenes de trabajo activas de la sucursal del usuario.
    """
    # 1. Aplicamos la regla Multi-Tenant estricta:
    sucursal_activa = request.user.sucursal

    # 2. Consultamos la base de datos (Excluimos las ENTREGADAS porque ya no están en el taller)
    # Usamos select_related para optimizar la consulta y no golpear la BD repetidamente en el template
    ordenes_base = OrdenTrabajo.objects.filter(
        sucursal=sucursal_activa
    ).exclude(
        estado='ENTREGADA'
    ).select_related('bicicleta__cliente', 'tecnico')

    # 3. Agrupamos las órdenes por estado para enviarlas a las columnas del Kanban
    context = {
        'ordenes_recibidas': ordenes_base.filter(estado='RECIBIDA'),
        'ordenes_diagnostico': ordenes_base.filter(estado='DIAGNOSTICO'),
        'ordenes_reparacion': ordenes_base.filter(estado='REPARACION'),
        'ordenes_esperando': ordenes_base.filter(estado='ESPERANDO_APROBACION'),
        'ordenes_listas': ordenes_base.filter(estado='LISTA'),
    }

    # 4. Renderizamos la plantilla (que crearemos en el paso 3)
    return render(request, 'taller/kanban.html', context)


@login_required
def nueva_orden(request):
    """Procesa el formulario de recepción de una nueva bicicleta"""
    tenant = request.user.tenant  # Lo guardamos en variable para reusarlo

    if request.method == 'POST':
        # Le pasamos el request.POST y los datos del usuario activo para los filtros
        form = OrdenTrabajoForm(request.POST, sucursal=request.user.sucursal, tenant=tenant)
        if form.is_valid():
            # Pausamos el guardado para inyectar los datos faltantes
            orden = form.save(commit=False)
            orden.sucursal = request.user.sucursal

            # ==========================================
            # MOTOR DE DETECCIÓN DE GARANTÍAS (30 DÍAS)
            # ==========================================
            hace_30_dias = timezone.now() - timedelta(days=30)

            # Buscamos si esta misma bicicleta tiene una orden terminada recientemente
            tuvo_servicio_reciente = OrdenTrabajo.objects.filter(
                bicicleta=orden.bicicleta,
                estado__in=['REPARADA', 'ENTREGADA'],
                created_at__gte=hace_30_dias
            ).exists()

            if tuvo_servicio_reciente:
                orden.es_posible_garantia = True
            # ==========================================

            # El cliente se deduce automáticamente de la bicicleta seleccionada
            orden.cliente = orden.bicicleta.cliente

            # Guardamos la orden para que se le asigne un ID en la base de datos
            orden.save()

            # --- INICIO NUEVA LÓGICA: INYECTAR SERVICIO ---
            servicio_id = request.POST.get('servicio_inicial')
            if servicio_id:
                servicio = ServicioCatalogo.objects.get(id=servicio_id, tenant=tenant)

                # Creamos el cargo asociado a esta orden
                CargoOrden.objects.create(
                    orden=orden,
                    descripcion=servicio.nombre,
                    precio=servicio.precio_base,
                    cantidad=1
                )

                # Actualizamos el total de la orden y guardamos de nuevo
                # orden.total_orden += servicio.precio_base
                # orden.save()
            # --- FIN NUEVA LÓGICA ---

            # Redirigimos al Kanban tras guardar con éxito
            return redirect('taller:kanban')
    else:
        # Si es un GET (entrar a la página), enviamos el formulario vacío
        form = OrdenTrabajoForm(sucursal=request.user.sucursal, tenant=tenant)

    # Traemos el catálogo de servicios de esta empresa para mandarlo a la plantilla
    servicios_disponibles = ServicioCatalogo.objects.filter(tenant=tenant).order_by('nombre')

    return render(request, 'taller/nueva_orden.html', {
        'form': form,
        'servicios_disponibles': servicios_disponibles  # Pasamos la lista de servicios
    })


@login_required
def buscar_bicicletas(request):
    """
    Vista llamada vía HTMX que busca bicicletas del Tenant activo
    basándose en el texto ingresado.
    """
    query = request.GET.get('q', '').strip()
    tenant = request.user.tenant

    if len(query) >= 2:
        # Buscamos coincidencias en marca, modelo o nombre del cliente
        # Respetando siempre la regla Multi-Tenant
        resultados = Bicicleta.objects.filter(
            Q(cliente__nombre__icontains=query) |
            Q(marca__icontains=query) |
            Q(modelo__icontains=query),
            cliente__tenant=tenant
        ).select_related('cliente')[:5]  # Limitamos a 5 resultados para no saturar
    else:
        resultados = []

    # Devolvemos SOLO un fragmento de HTML, no la página completa
    return render(request, 'taller/partials/resultados_bicicletas.html', {'resultados': resultados})


@login_required
def detalle_orden(request, pk):  # O el nombre que tenga tu vista
    orden = get_object_or_404(OrdenTrabajo, id=pk, sucursal=request.user.sucursal)

    # NUEVO: Traemos a los mecánicos de esta sucursal
    mecanicos = Usuario.objects.filter(rol='TECNICO', sucursal=request.user.sucursal)

    return render(request, 'taller/partials/detalle_orden_slideover.html', {
        'orden': orden,
        'mecanicos': mecanicos,
    })


@login_required
def subir_evidencia(request, pk):
    """
    Procesa la subida de UNO O VARIOS archivos multimedia (fotos/videos)
    desde la vista inspeccion_mecanico.
    Itera sobre request.FILES.getlist('archivos') y crea un registro
    Evidencia por cada archivo válido.
    """
    import os
    from .forms import EXTENSIONES_PERMITIDAS

    orden = get_object_or_404(OrdenTrabajo, id=pk, sucursal=request.user.sucursal)

    if request.method == 'POST':
        archivos = request.FILES.getlist('archivos')
        descripcion = request.POST.get('descripcion', '').strip()

        errores = []
        guardados = 0

        for archivo in archivos:
            _, ext = os.path.splitext(archivo.name)
            if ext.lower() not in EXTENSIONES_PERMITIDAS:
                errores.append(
                    f"'{archivo.name}' tiene un formato no permitido ({ext}). "
                    f"Solo se aceptan: {', '.join(sorted(EXTENSIONES_PERMITIDAS))}"
                )
                continue  # Saltamos este archivo pero seguimos con los demás

            Evidencia.objects.create(
                orden=orden,
                archivo=archivo,
                descripcion=descripcion,
            )
            guardados += 1

        if errores and guardados == 0:
            # Todos los archivos fallaron → volvemos a la pantalla con los errores
            return render(request, 'taller/inspeccion_mecanico.html', {
                'orden': orden,
                'evidencias': orden.evidencias.all(),
                'errores_evidencia': errores,
                'guardados_evidencia': guardados,
            }, status=422)

        # Al menos un archivo se guardó con éxito → volvemos al Kanban
        # (mismo comportamiento que "Guardar Hallazgo" en agregar_cargo_evidencia)
        return redirect('taller:kanban')

    return redirect('taller:kanban')


@login_required
def cambiar_estado_orden(request, pk, nuevo_estado):
    """Actualiza el estado de la orden en la base de datos"""
    if request.method == 'POST':
        orden = get_object_or_404(OrdenTrabajo, id=pk, sucursal=request.user.sucursal)

        if orden.estado != nuevo_estado:
            orden.estado = nuevo_estado
            orden.save()

        response = HttpResponse(status=200)
        response['HX-Refresh'] = 'true'
        return response

    return HttpResponse(status=400)


@login_required
def buscar_cargos(request, pk):
    """HTMX: Busca servicios y refacciones en tiempo real"""
    orden = get_object_or_404(OrdenTrabajo, id=pk, sucursal=request.user.sucursal)
    query = request.GET.get('q', '').strip()

    if query:
        # Buscamos en el inventario físico (máximo 5)
        refacciones = ItemInventario.objects.filter(
            Q(nombre__icontains=query) | Q(codigo_barras__icontains=query),
            sucursal=request.user.sucursal
        )[:5]

        # Buscamos en los servicios (máximo 5)
        servicios = ServicioCatalogo.objects.filter(
            nombre__icontains=query,
            tenant=request.user.tenant
        )[:5]

        return render(request, 'taller/partials/resultados_cargos.html', {
            'refacciones': refacciones,
            'servicios': servicios,
            'orden': orden
        })

    return HttpResponse('')  # Si borran el texto, regresamos vacío


@login_required
def agregar_servicio(request, pk, servicio_id):
    """Añade un servicio a la orden y devuelve la lista actualizada"""
    if request.method == 'POST':
        orden = get_object_or_404(OrdenTrabajo, id=pk, sucursal=request.user.sucursal)
        servicio = get_object_or_404(ServicioCatalogo, id=servicio_id, tenant=request.user.tenant)

        DetalleOrdenServicio.objects.create(
            orden=orden, servicio=servicio, precio_aplicado=servicio.precio_base
        )
        return render(request, 'taller/partials/lista_cargos.html', {'orden': orden})


@login_required
def agregar_pieza(request, pk, pieza_id):
    """Añade una pieza, descuenta el stock de forma segura y devuelve la lista"""
    if request.method == 'POST':
        orden = get_object_or_404(OrdenTrabajo, id=pk, sucursal=request.user.sucursal)

        with transaction.atomic():
            # Bloqueamos la fila (select_for_update) para evitar que dos mecánicos la tomen
            pieza = ItemInventario.objects.select_for_update().get(id=pieza_id, sucursal=request.user.sucursal)

            if pieza.stock > 0:
                DetalleOrdenPieza.objects.create(
                    orden=orden, item=pieza, cantidad=1, precio_aplicado=pieza.precio_venta
                )
                # Descontamos el stock a nivel de base de datos usando F()
                pieza.stock = F('stock') - 1
                pieza.save()

        return render(request, 'taller/partials/lista_cargos.html', {'orden': orden})


@login_required
def cobrar_orden(request, pk):
    """Procesa el pago de una orden y la marca como Entregada"""
    if request.method == 'POST':
        orden = get_object_or_404(OrdenTrabajo, id=pk, sucursal=request.user.sucursal)
        metodo_pago = request.POST.get('metodo_pago', 'EFECTIVO')

        with transaction.atomic():
            # 1. Creamos el registro del pago por el total de la orden
            Pago.objects.create(
                orden=orden,
                cajero=request.user,
                monto=orden.total_orden,
                metodo=metodo_pago
            )

            # 2. Actualizamos la orden
            orden.pagada = True
            orden.estado = 'ENTREGADA'  # Ya se pagó, ya se fue del taller
            orden.fecha_proximo_servicio = timezone.now().date() + timedelta(days=180)
            orden.save()

        # Refrescamos el tablero de HTMX para que la orden desaparezca de la vista activa
        response = HttpResponse(status=200)
        response['HX-Refresh'] = 'true'
        return response


def rastreo_publico(request, token):
    """
    Vista pública para que el cliente vea el estado de su bicicleta.
    No requiere autenticación. Protege los datos personales.
    """
    # Buscamos la orden usando únicamente el token seguro
    # select_related optimiza la consulta trayendo la bici, cliente y sucursal de un solo golpe
    orden = get_object_or_404(
        OrdenTrabajo.objects.select_related('bicicleta__cliente', 'sucursal__tenant'),
        uuid_publico=token)

    progreso = {
        'RECIBIDA': 25,
        'DIAGNOSTICO': 50,
        'REPARACION': 75,
        'REPARADA': 100,
        'ENTREGADA': 100
    }.get(orden.estado, 0)

    # Renderizamos una plantilla específica para el cliente, sin los menús del taller
    return render(request, 'taller/rastreo_publico.html', {
        'orden': orden,
        'progreso': progreso
    })


@login_required
@roles_permitidos('ADMIN', 'CAJERO')
def dashboard_inicio(request):
    """Muestra los indicadores clave (KPIs) del día para la sucursal activa."""
    sucursal = request.user.sucursal
    hoy = timezone.localdate()

    # 1. Ingresos del Día (Sumamos los pagos creados hoy en esta sucursal)
    pagos_hoy = Pago.objects.filter(
        orden__sucursal=sucursal,
        fecha__date=hoy
    )

    ingreso_total = pagos_hoy.aggregate(Sum('monto'))['monto__sum'] or 0
    ingreso_efectivo = pagos_hoy.filter(metodo='EFECTIVO').aggregate(Sum('monto'))['monto__sum'] or 0
    ingreso_tarjeta = pagos_hoy.exclude(metodo='EFECTIVO').aggregate(Sum('monto'))['monto__sum'] or 0

    # 2. Métricas Operativas
    bicis_recibidas_hoy = OrdenTrabajo.objects.filter(
        sucursal=sucursal,
        created_at__date=hoy
    ).count()

    bicis_listas = OrdenTrabajo.objects.filter(
        sucursal=sucursal,
        estado='LISTA'
    ).count()

    # 3. Próximas entregas (Para mostrar una pequeña lista rápida)
    proximas_entregas = OrdenTrabajo.objects.filter(
        sucursal=sucursal,
        estado__in=['LISTA', 'REPARACION']
    ).select_related('bicicleta__cliente').order_by('-updated_at')[:5]

    # 4. Proveedores esperados hoy
    # Mapeamos el weekday() de Python (0=Lunes) a nombres en español con
    # dos variantes por día que tenga acento, para hacer el icontains robusto
    # contra registros escritos con o sin tilde.
    DIAS_SEMANA = {
        0: ['Lunes'],
        1: ['Martes'],
        2: ['Miércoles', 'Miercoles'],
        3: ['Jueves'],
        4: ['Viernes'],
        5: ['Sábado', 'Sabado'],
        6: ['Domingo'],
    }
    dia_actual = DIAS_SEMANA[timezone.now().weekday()][0]   # nombre canónico (con acento)
    variantes_dia = DIAS_SEMANA[timezone.now().weekday()]   # lista con todas las variantes

    # Construimos un filtro OR para cada variante del nombre del día
    filtro_dia = Q()
    for variante in variantes_dia:
        filtro_dia |= Q(dias_visita__icontains=variante)

    proveedores_hoy = Proveedor.objects.filter(
        filtro_dia,
        sucursal=sucursal,
        activo=True,
    )

    # 5. Citas de hoy (solo si el módulo de citas está activo para este tenant)
    if request.user.tenant.modulo_citas:
        citas_hoy = Cita.objects.filter(
            sucursal=sucursal,
            fecha=hoy,
            estado='PENDIENTE',
        ).order_by('hora')
    else:
        citas_hoy = Cita.objects.none()

    context = {
        'ingreso_total': ingreso_total,
        'ingreso_efectivo': ingreso_efectivo,
        'ingreso_tarjeta': ingreso_tarjeta,
        'bicis_recibidas_hoy': bicis_recibidas_hoy,
        'bicis_listas': bicis_listas,
        'proximas_entregas': proximas_entregas,
        'hoy': hoy,
        'proveedores_hoy': proveedores_hoy,
        'dia_actual': dia_actual,
        'citas_hoy': citas_hoy,
    }

    return render(request, 'taller/dashboard_inicio.html', context)


@login_required
@modulo_requerido('modulo_citas')
def agenda_citas(request):
    """Muestra la agenda y permite crear nuevas citas"""
    sucursal = request.user.sucursal
    tenant = request.user.tenant
    hoy = timezone.localdate()

    if request.method == 'POST':
        form = CitaForm(request.POST, tenant=tenant, sucursal=sucursal)
        if form.is_valid():
            nueva_cita = form.save(commit=False)
            nueva_cita.sucursal = sucursal
            nueva_cita.save()
            return redirect('taller:agenda')
    else:
        form = CitaForm(initial={'fecha': hoy}, tenant=tenant, sucursal=sucursal)

    # Traemos las citas de HOY en adelante, que no estén canceladas
    citas = Cita.objects.filter(
        sucursal=sucursal,
        fecha=hoy
    ).order_by('hora')

    return render(request, 'taller/agenda.html', {
        'form': form,
        'citas': citas
    })


@login_required
@modulo_requerido('modulo_citas')
def marcar_cita_atendida(request, pk):
    """HTMX: Cambia el estado a atendida y redirige inyectando los datos del cliente"""
    if request.method == 'POST':
        cita = get_object_or_404(Cita, id=pk, sucursal=request.user.sucursal)
        cita.estado = 'ATENDIDA'
        cita.save()

        # 1. URL base
        base_url = reverse('taller:nueva_orden')

        # 2. Empaquetamos el nombre y teléfono de forma segura para la URL
        parametros = urllib.parse.urlencode({
            'nombre': cita.nombre_cliente,
            'telefono': cita.telefono
        })

        # 3. Unimos: /taller/nueva-orden/?nombre=Juan&telefono=5551234
        url_final = f"{base_url}?{parametros}"

        response = HttpResponse()
        response['HX-Redirect'] = url_final
        return response

    return HttpResponse(status=400)


@login_required
@roles_permitidos('ADMIN')
def corte_caja(request):
    """Genera el resumen de pagos del día para la sucursal activa"""
    sucursal = request.user.sucursal
    # Usamos timezone.localdate() para respetar la zona horaria de settings.py
    hoy = timezone.localdate()

    # Traemos todos los pagos de HOY que pertenezcan a órdenes de esta sucursal
    pagos_hoy = Pago.objects.filter(
        orden__sucursal=sucursal,
        fecha__date=hoy
    ).select_related('orden__bicicleta__cliente', 'cajero').order_by('-fecha')

    # Sumatorias por metodo de pago
    total_efectivo = pagos_hoy.filter(metodo='EFECTIVO').aggregate(Sum('monto'))['monto__sum'] or 0
    total_tarjeta = pagos_hoy.filter(metodo='TARJETA').aggregate(Sum('monto'))['monto__sum'] or 0
    total_transfer = pagos_hoy.filter(metodo='TRANSFERENCIA').aggregate(Sum('monto'))['monto__sum'] or 0

    gran_total = total_efectivo + total_tarjeta + total_transfer

    context = {
        'pagos': pagos_hoy,
        'total_efectivo': total_efectivo,
        'total_tarjeta': total_tarjeta,
        'total_transfer': total_transfer,
        'gran_total': gran_total,
        'hoy': hoy,
    }

    return render(request, 'taller/corte_caja.html', context)


@login_required
def agregar_cargo(request, pk):
    """HTMX: Agrega el ítem clickeado a la orden y devuelve la lista actualizada"""
    if request.method == 'POST':
        orden = get_object_or_404(OrdenTrabajo, id=pk, sucursal=request.user.sucursal)
        tipo = request.POST.get('tipo')
        item_id = request.POST.get('item_id')

        if tipo == 'refaccion':
            item = get_object_or_404(ItemInventario, id=item_id, sucursal=request.user.sucursal)

            # Solo agregamos si hay stock
            if item.stock > 0:
                CargoOrden.objects.create(
                    orden=orden,
                    descripcion=item.nombre,
                    precio=item.precio_venta,
                    cantidad=1
                )
                # Descontamos 1 del inventario físico
                item.stock -= 1
                item.save()

        elif tipo == 'servicio':
            servicio = get_object_or_404(ServicioCatalogo, id=item_id, tenant=request.user.tenant)
            CargoOrden.objects.create(
                orden=orden,
                descripcion=servicio.nombre,
                precio=servicio.precio_base,
                cantidad=1
            )

        orden = OrdenTrabajo.objects.get(id=orden.id)

        # Devolvemos la lista de cargos actualizada Y un pequeño script para limpiar el buscador
        html_lista = render(request, 'taller/partials/lista_cargos.html', {'orden': orden}).content.decode('utf-8')
        # 1. El script que ya tenías
        script_limpieza = """
                    <script>
                        document.querySelector('input[name="q"]').value = '';
                        document.getElementById('resultados-cargos-container').innerHTML = '';
                    </script>
                """

        # 2. EL FRAGMENTO OOB: Nota el atributo hx-swap-oob="true" y que el ID coincide exactamente
        html_oob = f"""
                    <span id="monto-cobro-oob" hx-swap-oob="true" class="text-green-600">
                        ${orden.total_orden:.2f}
                    </span>
                """
        # Devolvemos las 3 cosas juntas
        return HttpResponse(html_lista + script_limpieza + html_oob)

    return HttpResponse(status=400)


@login_required
def eliminar_cargo(request, cargo_id):
    """HTMX: Elimina un cargo de la orden y actualiza la vista"""
    if request.method == 'POST':
        # Buscamos el cargo asegurándonos que pertenece a la sucursal del usuario
        cargo = get_object_or_404(CargoOrden, id=cargo_id, orden__sucursal=request.user.sucursal)
        orden = cargo.orden

        # Eliminamos el cargo
        cargo.delete()

        # ¡LA LÍNEA MÁGICA! Forzamos a Django a olvidar la caché y recalcular el total
        orden = OrdenTrabajo.objects.get(id=orden.id)

        # Después de orden = OrdenTrabajo.objects.get(id=orden.id)
        html_lista = render(request, 'taller/partials/lista_cargos.html', {'orden': orden}).content.decode('utf-8')

        # EL FRAGMENTO OOB
        html_oob = f"""
                    <span id="monto-cobro-oob" hx-swap-oob="true" class="text-green-600">
                        ${orden.total_orden:.2f}
                    </span>
                """

        return HttpResponse(html_lista + html_oob)
    return HttpResponse(status=400)


@login_required
@modulo_requerido('modulo_citas')
def recibir_cita(request, pk):
    """Convierte una Cita en Orden de Trabajo inteligente"""
    if request.method == 'POST':
        cita = get_object_or_404(Cita, id=pk, sucursal=request.user.sucursal)

        if cita.estado != 'COMPLETADA':

            # CASO 1: Cita de cliente recurrente (Tiene bicicleta vinculada)
            if cita.bicicleta:
                OrdenTrabajo.objects.create(
                    sucursal=cita.sucursal,
                    cliente=cita.bicicleta.cliente,
                    bicicleta=cita.bicicleta,
                    estado='RECIBIDA',
                    notas_cliente=cita.asunto,  # Usamos el asunto como notas iniciales
                )
                cita.estado = 'ATENDIDA'
                cita.save()

                # Magia HTMX: Redirección directa al Kanban
                response = HttpResponse(status=200)
                response['HX-Redirect'] = reverse('taller:kanban')
                return response

            # CASO 2: Cita de cliente nuevo (No tiene bicicleta vinculada)
            else:
                cita.estado = 'ATENDIDA'
                cita.save()

                # Lo mandamos a registrar su bici, pero le pre-llenamos el nombre y teléfono
                base_url = reverse('taller:nueva_orden')
                parametros = urllib.parse.urlencode({
                    'nombre': cita.nombre_cliente,
                    'telefono': cita.telefono
                })
                url_final = f"{base_url}?{parametros}"

                response = HttpResponse(status=200)
                response['HX-Redirect'] = url_final
                return response

    return HttpResponse(status=400)


@login_required
def imprimir_ticket(request, pk):
    """Genera una vista optimizada para impresoras térmicas (Punto de Venta)"""
    # Nos aseguramos de que la orden pertenece a la sucursal del usuario
    orden = get_object_or_404(OrdenTrabajo, id=pk, sucursal=request.user.sucursal)

    return render(request, 'taller/imprimir_ticket.html', {
        'orden': orden
    })


@login_required
def notificar_whatsapp(request, pk):
    """Genera un enlace dinámico de WhatsApp según el estado de la orden"""
    orden = get_object_or_404(OrdenTrabajo, id=pk, sucursal=request.user.sucursal)
    cliente = orden.cliente

    nombre_empresa = orden.sucursal.tenant.nombre
    nombre_sucursal = orden.sucursal.nombre
    estado_display = orden.get_estado_display()

    # Limpiamos el teléfono (quitamos espacios o guiones si los hay)
    telefono = cliente.telefono.replace(' ', '').replace('-', '')

    url_rastreo = request.build_absolute_uri(reverse('taller:rastreo_publico', kwargs={'token': orden.uuid_publico}))

    if orden.estado == 'RECIBIDA' or orden.estado == 'DIAGNOSTICO':
        mensaje = (
            f"¡Hola {cliente.nombre}! Te contactamos de {nombre_empresa} (Suc. {nombre_sucursal}) 🚲.\n\n"
            f"El presupuesto estimado para tu {orden.bicicleta.marca} es de ${orden.total_orden}.\n"
            f"¿Nos autorizas a iniciar?\n\n"
            f"📍 Sigue el estatus y el detalle aquí:\n{url_rastreo}"
        )
    elif orden.estado == 'ESPERANDO_APROBACION':
        mensaje = (
            f"¡Hola {cliente.nombre}! Te contactamos de {nombre_empresa} (Suc. {nombre_sucursal}) ⚠️.\n\n"
            f"Durante la revisión, nuestro mecánico encontró un detalle que requiere tu autorización.\n\n"
            f"📍 Revisa la evidencia fotográfica y aprueba el cambio aquí:\n{url_rastreo}"
        )
    elif orden.estado == 'REPARADA':
        mensaje = (
            f"¡Excelentes noticias {cliente.nombre}! 🥳\n\n"
            f"El servicio de tu {orden.bicicleta.marca} ya quedó listo en {nombre_empresa} (Suc. {nombre_sucursal}). El saldo a liquidar es de ${orden.total_orden}.\n\n"
            f"📍 Ya puedes pasar a recogerla. Mira el detalle final aquí:\n{url_rastreo}"
        )
    else:
        mensaje = (
            f"¡Hola {cliente.nombre}! Te contactamos de {nombre_empresa} (Suc. {nombre_sucursal}) 🚲.\n\n"
            f"El estatus actual de tu bicicleta es: {estado_display}.\n\n"
            f"📍 Sigue el avance en tiempo real aquí:\n{url_rastreo}"
        )

    # 2. Codificamos el texto para que la URL sea válida
    mensaje_codificado = urllib.parse.quote(mensaje)

    # 3. Construimos el enlace oficial de WhatsApp (wa.me)
    url_whatsapp = f"https://wa.me/{telefono}?text={mensaje_codificado}"

    # Redirigimos al usuario hacia WhatsApp (Web o App)
    return redirect(url_whatsapp)


@login_required
def avanzar_estado_orden(request, pk):
    """HTMX: Mueve la orden a la siguiente columna lógica del Kanban"""
    if request.method == 'POST':
        orden = get_object_or_404(OrdenTrabajo, id=pk, sucursal=request.user.sucursal)

        # Diccionario de transiciones lógicas
        # Formato: 'ESTADO_ACTUAL': 'SIGUIENTE_ESTADO'
        transiciones = {
            'RECIBIDA': 'DIAGNOSTICO',
            'DIAGNOSTICO': 'EN_REPARACION',
            'EN_REPARACION': 'REPARADA',
            # Nota: No automatizamos el paso a ENTREGADA aquí porque
            # eso requiere el proceso de cobro.
        }

        if orden.estado in transiciones:
            orden.estado = transiciones[orden.estado]
            orden.save()

        # Magia HTMX: Redirigimos al Kanban para ver el cambio reflejado
        response = HttpResponse(status=200)
        response['HX-Redirect'] = reverse('taller:kanban')
        return response

    return HttpResponse(status=400)


@login_required
@roles_permitidos('ADMIN')
def dashboard_analitico(request):
    """Vista principal de métricas y analítica del taller"""
    sucursal = request.user.sucursal
    hoy = timezone.now().date()
    inicio_mes = hoy.replace(day=1)

    # 1. MÉTRICAS GENERALES (Las tarjetas superiores)
    bicis_en_taller = OrdenTrabajo.objects.filter(
        sucursal=sucursal,
        estado__in=['RECIBIDA', 'DIAGNOSTICO', 'ESPERANDO_APROBACION', 'REPARACION']
    ).count()

    citas_hoy = Cita.objects.filter(
        sucursal=sucursal, fecha=hoy, estado='PENDIENTE'
    ).count()

    ingresos_mes = CargoOrden.objects.filter(
        orden__sucursal=sucursal,
        orden__estado__in=['REPARADA', 'ENTREGADA'],
        estado_aprobacion='APROBADO', # Excluimos los rechazados
        created_at__date__gte=inicio_mes
    ).aggregate(total=Sum(F('cantidad') * F('precio')))['total'] or 0.00

    # 2. TOP MECÁNICOS DEL MES (Productividad)
    # Asumiendo que OrdenTrabajo tiene un campo ForeignKey 'mecanico'
    top_mecanicos = OrdenTrabajo.objects.filter(
        sucursal=sucursal,
        estado__in=['REPARADA', 'ENTREGADA'],
        created_at__date__gte=inicio_mes
    ).values('tecnico__username', 'tecnico__first_name', 'tecnico__last_name').annotate(
        total_ordenes=Count('id')
    ).order_by('-total_ordenes')[:5]

    # 3. TOP SERVICIOS Y REFACCIONES (Lo que más se vende)
    top_servicios = CargoOrden.objects.filter(
        orden__sucursal=sucursal,
        orden__estado__in=['REPARADA', 'ENTREGADA'],
        estado_aprobacion='APROBADO',
        created_at__date__gte=inicio_mes
    ).values('descripcion').annotate(
        cantidad_vendida=Sum('cantidad'),
        ingreso_generado=Sum(F('cantidad') * F('precio'))
    ).order_by('-cantidad_vendida')[:5]

    oportunidades_recompra = OrdenTrabajo.objects.filter(
        sucursal=sucursal,
        estado='ENTREGADA',
        fecha_proximo_servicio__lte=hoy,  # Solo comparamos si la fecha proyectada ya es hoy o pasó
        recordatorio_enviado=False
    ).count()

    # 4. TENDENCIA DE VENTAS (Gráfica de los últimos 6 meses)
    hace_6_meses = hoy - timedelta(days=180)
    tendencia_mensual = CargoOrden.objects.filter(
        orden__sucursal=sucursal,
        orden__estado__in=['REPARADA', 'ENTREGADA'],
        estado_aprobacion='APROBADO',
        created_at__date__gte=hace_6_meses
    ).annotate(
        mes=TruncMonth('created_at')
    ).values('mes').annotate(
        total=Sum(F('cantidad') * F('precio'))
    ).order_by('mes')

    meses_labels = [v['mes'].strftime("%b %Y").capitalize() for v in tendencia_mensual]
    meses_totales = [float(v['total'] or 0) for v in tendencia_mensual]

    context = {
        'bicis_en_taller': bicis_en_taller,
        'citas_hoy': citas_hoy,
        'ingresos_mes': ingresos_mes,
        'mes_actual': hoy.strftime("%B").capitalize(),
        'top_mecanicos': top_mecanicos,
        'top_servicios': top_servicios,
        'chart_labels': json.dumps(meses_labels),
        'chart_data': json.dumps(meses_totales),
        'oportunidades_recompra': oportunidades_recompra,
    }

    return render(request, 'taller/dashboard_analitico.html', context)


@login_required
@admin_requerido
def gestion_personal(request):
    """CRUD para gestionar a los empleados de la sucursal"""
    sucursal = request.user.sucursal
    tenant = request.user.tenant

    if request.method == 'POST':
        form = EmpleadoForm(request.POST)
        if form.is_valid():
            # Pausamos el guardado para inyectar sucursal, tenant y encriptar contraseña
            nuevo_empleado = form.save(commit=False)
            nuevo_empleado.sucursal = sucursal
            nuevo_empleado.tenant = tenant

            # ¡Muy importante! Encriptar la contraseña antes de guardar
            nuevo_empleado.password = make_password(form.cleaned_data['password'])
            nuevo_empleado.save()

            return redirect('taller:gestion_personal')
    else:
        form = EmpleadoForm()

    # Traemos a todos los empleados de ESTA sucursal (excluyendo al superusuario global si existe)
    empleados = Usuario.objects.filter(sucursal=sucursal).order_by('rol', 'first_name')

    return render(request, 'taller/personal.html', {
        'form': form,
        'empleados': empleados
    })


@login_required
@admin_requerido
def editar_empleado(request, pk):
    """HTMX: Carga el formulario de edición y procesa los cambios"""
    empleado = get_object_or_404(Usuario, id=pk, sucursal=request.user.sucursal)

    if request.method == 'POST':
        form = EmpleadoForm(request.POST, instance=empleado)
        form.fields['password'].required = False  # La contraseña es opcional al editar

        if form.is_valid():
            empleado_guardado = form.save(commit=False)
            nueva_password = form.cleaned_data.get('password')
            if nueva_password:
                empleado_guardado.password = make_password(nueva_password)
            empleado_guardado.save()

            # Recargamos la pantalla completa para ver la lista actualizada
            response = HttpResponse(status=200)
            response['HX-Redirect'] = reverse('taller:gestion_personal')
            return response
    else:
        form = EmpleadoForm(instance=empleado)
        form.fields['password'].required = False

    # Devolvemos solo el HTML del formulario para inyectarlo en la columna izquierda
    return render(request, 'taller/partials/form_empleado.html', {'form': form, 'empleado': empleado})


@login_required
@admin_requerido
def toggle_estado_empleado(request, pk):
    """HTMX: Baja o Alta Lógica de un empleado"""
    if request.method == 'POST':
        empleado = get_object_or_404(Usuario, id=pk, sucursal=request.user.sucursal)

        # Seguridad: El administrador no puede desactivarse a sí mismo por error
        if empleado != request.user:
            empleado.is_active = not empleado.is_active
            empleado.save()

        response = HttpResponse(status=200)
        response['HX-Redirect'] = reverse('taller:gestion_personal')
        return response

    return HttpResponse(status=400)


@login_required
def agregar_cargo_evidencia(request, pk):
    """HTMX: Agrega un cargo extra, sube la foto y pausa la orden si requiere aprobación"""
    if request.method == 'POST':
        orden = get_object_or_404(OrdenTrabajo, id=pk, sucursal=request.user.sucursal)

        # 1. Capturamos los datos del formulario
        descripcion = request.POST.get('descripcion')
        precio = request.POST.get('precio')
        cantidad = request.POST.get('cantidad', 1)

        # 2. Capturamos los campos Premium
        requiere_aprobacion = request.POST.get('requiere_aprobacion') == 'on'
        evidencia_nota = request.POST.get('evidencia_nota')
        evidencia_foto = request.FILES.get('evidencia_foto')  # ¡Ojo aquí! Usamos request.FILES

        # 3. Creamos el registro en la base de datos
        nuevo_cargo = CargoOrden.objects.create(
            orden=orden,
            descripcion=descripcion,
            precio=precio,
            cantidad=cantidad,
            requiere_aprobacion=requiere_aprobacion,
            evidencia_nota=evidencia_nota,
            evidencia_foto=evidencia_foto,
            estado_aprobacion='PENDIENTE' if requiere_aprobacion else 'APROBADO'
        )

        # 4. Magia de la Máquina de Estados
        if requiere_aprobacion:
            orden.estado = 'ESPERANDO_APROBACION'
            orden.save()
            # Si se pausa el trabajo, cerramos el panel y recargamos el Kanban
            return redirect('taller:kanban')

        # Si no requiere aprobación, solo recargamos la lista de cargos en el panel
        # (Asegúrate de tener una URL/vista que devuelva solo el HTML de los cargos)
        return redirect('taller:kanban')

    return HttpResponse(status=400)


@login_required
def inspeccion_mecanico(request, pk):
    """Pantalla vertical dedicada para que el mecánico registre hallazgos y suba evidencias"""
    orden = get_object_or_404(OrdenTrabajo, id=pk, sucursal=request.user.sucursal)

    return render(request, 'taller/inspeccion_mecanico.html', {
        'orden': orden,
        'evidencia_form': EvidenciaForm(),
        'evidencias': orden.evidencias.all(),
    })


def responder_aprobacion(request, token, accion):
    """Procesa la decisión del cliente sobre el presupuesto extra"""
    if request.method == 'POST':
        orden = get_object_or_404(OrdenTrabajo, uuid_publico=token)

        # Buscamos todos los cargos de esta orden que están en pausa
        cargos_pendientes = CargoOrden.objects.filter(orden=orden, estado_aprobacion='PENDIENTE')

        if accion == 'aprobar':
            # Marcamos los cargos como aceptados
            cargos_pendientes.update(estado_aprobacion='APROBADO')
        elif accion == 'rechazar':
            # Marcamos los cargos como rechazados (no sumarán al total)
            cargos_pendientes.update(estado_aprobacion='RECHAZADO')

        # Magia: Movemos la tarjeta de vuelta a la fila de los mecánicos
        orden.estado = 'REPARACION'
        orden.save()

        # Redirigimos al cliente de vuelta a su página de rastreo para que vea el nuevo avance
        # NOTA: Cambia 'pk' por el nombre de parámetro que uses en tu URL original (ej. 'uuid')
        return redirect('taller:rastreo_publico', token=orden.uuid_publico)

    return HttpResponse(status=400)


@login_required
@roles_permitidos('ADMIN', 'CAJERO')
@modulo_requerido('modulo_retencion')
def panel_retencion(request):
    """Muestra los clientes que requieren un servicio de mantenimiento próximo/vencido"""
    hoy = timezone.now().date()

    # Filtramos órdenes entregadas cuya fecha de próximo servicio ya llegó y no han sido contactados
    recordatorios = OrdenTrabajo.objects.filter(
        sucursal=request.user.sucursal,
        estado='ENTREGADA',
        fecha_proximo_servicio__lte=hoy,
        recordatorio_enviado=False
    ).select_related('cliente', 'bicicleta').order_by('fecha_proximo_servicio')

    return render(request, 'taller/retencion.html', {'recordatorios': recordatorios})


@login_required
@roles_permitidos('ADMIN', 'CAJERO')
def marcar_recordatorio(request, pk):
    """HTMX Endpoint para marcar como enviado y desaparecer la fila"""
    if request.method == 'POST':
        orden = get_object_or_404(OrdenTrabajo, id=pk, sucursal=request.user.sucursal)
        orden.recordatorio_enviado = True
        orden.save()

        # Devolvemos un HttpResponse vacío.
        # HTMX reemplazará la fila (<tr>) con esto, haciéndola desaparecer al instante.
        return HttpResponse("")
