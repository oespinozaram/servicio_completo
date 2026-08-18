from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.db.models.functions import TruncDate
from .forms import OrdenTrabajoForm, CitaForm
from django.db.models import Q, F
from clientes.models import Bicicleta
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from inventario.models import ServicioCatalogo, ItemInventario
from .models import DetalleOrdenServicio, DetalleOrdenPieza, Pago, Cita, CargoOrden, OrdenTrabajo
from .forms import EmpleadoForm
from django.db import transaction
from django.db.models import Sum
from django.urls import reverse
import urllib.parse
from django.utils import timezone
from datetime import timedelta
import json
from .decorators import admin_requerido
from core.decorators import modulo_requerido
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
        'mecanicos': mecanicos  # <-- Asegúrate de mandar esta variable
    })


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
        token_publico=token
    )

    # Renderizamos una plantilla específica para el cliente, sin los menús del taller
    return render(request, 'taller/rastreo_publico.html', {'orden': orden})


@login_required
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

    context = {
        'ingreso_total': ingreso_total,
        'ingreso_efectivo': ingreso_efectivo,
        'ingreso_tarjeta': ingreso_tarjeta,
        'bicis_recibidas_hoy': bicis_recibidas_hoy,
        'bicis_listas': bicis_listas,
        'proximas_entregas': proximas_entregas,
        'hoy': hoy,
    }

    return render(request, 'taller/dashboard.html', context)


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

        # 3. Unimos todo: /taller/nueva-orden/?nombre=Juan&telefono=5551234
        url_final = f"{base_url}?{parametros}"

        response = HttpResponse()
        response['HX-Redirect'] = url_final
        return response

    return HttpResponse(status=400)


@login_required
@admin_requerido
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

    # Limpiamos el teléfono (quitamos espacios o guiones si los hay)
    telefono = cliente.telefono.replace(' ', '').replace('-', '')

    # Opcional: Si tus clientes no guardan el código de país, puedes forzarlo aquí.
    # if not telefono.startswith('+'):
    #     telefono = f"+52{telefono}"

    # 1. Analizamos el estado para redactar el mensaje
    if orden.estado == 'RECIBIDA' or orden.estado == 'DIAGNOSTICO':
        mensaje = (
            f"¡Hola {cliente.nombre}! Te contactamos de *{orden.sucursal.nombre}* 🚲.\n\n"
            f"El presupuesto estimado para tu {orden.bicicleta.marca} es de *${orden.total_orden}*.\n"
            f"¿Nos autorizas a iniciar con el servicio?"
        )
    elif orden.estado == 'REPARADA':
        mensaje = (
            f"¡Excelentes noticias {cliente.nombre}! 🥳\n\n"
            f"El servicio de tu {orden.bicicleta.marca} ya quedó listo. "
            f"El saldo a liquidar es de *${orden.total_orden}*.\n\n"
            f"Ya puedes pasar a recogerla a nuestro taller. ¡Te esperamos!"
        )
    else:
        mensaje = (
            f"¡Hola {cliente.nombre}! Te contactamos de *{orden.sucursal.nombre}* "
            f"para darte seguimiento a la orden de tu bicicleta."
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
@admin_requerido
def dashboard(request):
    sucursal = request.user.sucursal
    hoy = timezone.now().date()
    inicio_mes = hoy.replace(day=1)
    hace_una_semana = hoy - timedelta(days=7)  # Rango para la gráfica

    bicis_en_taller = OrdenTrabajo.objects.filter(
        sucursal=sucursal,
        estado__in=['RECIBIDA', 'DIAGNOSTICO', 'EN_REPARACION']
    ).count()

    # 2. Citas Agendadas para Hoy
    citas_hoy = Cita.objects.filter(
        sucursal=sucursal,
        fecha=hoy,
        estado='PENDIENTE'
    ).count()

    # 3. Ingresos del Mes (Calculado directo desde la base de datos multiplicando cant * precio)
    # Asumimos que los ingresos reales son de las bicis "REPARADAS" o entregadas.
    ingresos_mes = CargoOrden.objects.filter(
        orden__sucursal=sucursal,
        orden__estado__in=['REPARADA'],  # O el estado final que manejes
        created_at__date__gte=inicio_mes
    ).aggregate(
        total=Sum(F('cantidad') * F('precio'))
    )['total'] or 0.00

    # 4. NUEVO: Datos para la gráfica (Ingresos de los últimos 7 días)
    # Agrupamos los cargos por fecha exacta y sumamos los totales
    ingresos_diarios = CargoOrden.objects.filter(
        orden__sucursal=sucursal,
        orden__estado='REPARADA',  # Asegúrate de usar el estado correcto de "cobro"
        created_at__date__gte=hace_una_semana
    ).annotate(
        fecha=TruncDate('created_at')
    ).values('fecha').annotate(
        total_dia=Sum(F('cantidad') * F('precio'))
    ).order_by('fecha')

    # Extraemos los datos en dos listas simples para inyectarlas en Chart.js
    etiquetas = [ingreso['fecha'].strftime("%d %b") for ingreso in ingresos_diarios]
    totales = [float(ingreso['total_dia'] or 0) for ingreso in ingresos_diarios]

    context = {
        'bicis_en_taller': bicis_en_taller,
        'citas_hoy': citas_hoy,
        'ingresos_mes': ingresos_mes,
        'mes_actual': hoy.strftime("%B").capitalize(),

        # Pasamos las listas al HTML convertidas en texto JSON seguro
        'chart_labels': json.dumps(etiquetas),
        'chart_data': json.dumps(totales),
    }

    #return render(request, 'taller/dashboard.html', context)
    return render(request, 'taller/dashboard2.html', context)


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
