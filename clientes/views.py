# clientes/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .forms import ClienteForm, BicicletaForm
from .models import Cliente
from django.shortcuts import get_object_or_404
from taller.models import OrdenTrabajo
from django.db.models import Count, Q


@login_required
def nuevo_cliente_bici(request):
    if request.method == 'POST':
        cliente_form = ClienteForm(request.POST)
        bici_form = BicicletaForm(request.POST)

        if cliente_form.is_valid() and bici_form.is_valid():
            # Usamos atomic para evitar datos a medias si algo falla
            with transaction.atomic():
                # 1. Guardamos al Cliente asignándole el Tenant del usuario activo
                cliente = cliente_form.save(commit=False)
                cliente.tenant = request.user.tenant
                cliente.save()

                # 2. Guardamos la Bicicleta ligándola al cliente recién creado
                bici = bici_form.save(commit=False)
                bici.cliente = cliente
                bici.save()

            # Redirigimos de vuelta al mostrador (Nueva Orden)
            return redirect('taller:nueva_orden')
    else:
        cliente_form = ClienteForm()
        bici_form = BicicletaForm()

    return render(request, 'clientes/nuevo_cliente_bici.html', {
        'cliente_form': cliente_form,
        'bici_form': bici_form
    })


@login_required
def directorio_clientes(request):
    """Muestra el directorio con buscador en tiempo real (HTMX)"""

    # 1. Atrapamos el texto de búsqueda si existe
    query = request.GET.get('q', '')

    try:
        clientes = Cliente.objects.filter(tenant=request.user.tenant)
    except:
        clientes = Cliente.objects.all()

    # 2. Si el usuario escribió algo, filtramos por nombre o teléfono
    if query:
        clientes = clientes.filter(
            Q(nombre__icontains=query) | Q(telefono__icontains=query)
        )

    clientes = clientes.annotate(num_bicis=Count('bicicletas')).order_by('nombre')

    # 3. MAGIA HTMX: Si es una búsqueda en vivo, solo devolvemos las filas de la tabla
    if request.headers.get('HX-Request'):
        return render(request, 'clientes/partials/filas_directorio.html', {'clientes': clientes})

    # Si es una carga de página normal, devolvemos todo completo
    return render(request, 'clientes/directorio.html', {'clientes': clientes})


@login_required
def perfil_cliente(request, pk):
    """Muestra el detalle del cliente y todo su historial de reparaciones"""

    # Buscamos al cliente (respetando el Tenant si lo tienes configurado)
    try:
        cliente = get_object_or_404(Cliente, id=pk, tenant=request.user.tenant)
    except:
        cliente = get_object_or_404(Cliente, id=pk)

    # Magia de Django (Relaciones inversas):
    # Buscamos todas las órdenes cuya bicicleta pertenezca a este cliente.
    # order_by('-created_at') pone las más recientes primero.
    historial = OrdenTrabajo.objects.filter(
        bicicleta__cliente=cliente
    ).select_related('bicicleta', 'sucursal').order_by('-created_at')

    return render(request, 'clientes/perfil.html', {
        'cliente': cliente,
        'historial': historial
    })
