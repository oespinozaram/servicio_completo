from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from .models import ItemInventario, ServicioCatalogo
from .forms import ItemInventarioForm, ServicioCatalogoForm


@login_required
def lista_inventario(request):
    """Muestra el catálogo de refacciones y procesa el formulario de nuevas piezas"""
    sucursal = request.user.sucursal

    # Procesar nueva pieza si es POST
    if request.method == 'POST':
        form = ItemInventarioForm(request.POST)
        if form.is_valid():
            nuevo_item = form.save(commit=False)
            nuevo_item.sucursal = sucursal
            nuevo_item.save()
            return redirect('inventario:lista')
    else:
        form = ItemInventarioForm()

    # Obtener inventario de esta sucursal (regla Multi-Tenant)
    items = ItemInventario.objects.filter(sucursal=sucursal).order_by('nombre')

    return render(request, 'inventario/lista.html', {
        'items': items,
        'form': form
    })


@login_required
def actualizar_stock(request, pk):
    """Vista HTMX para edición en línea: actualiza el stock y devuelve un check visual"""
    if request.method == 'POST':
        item = get_object_or_404(ItemInventario, id=pk, sucursal=request.user.sucursal)
        nuevo_stock = request.POST.get('stock')

        if nuevo_stock is not None and nuevo_stock.isdigit():
            item.stock = int(nuevo_stock)
            item.save()

            # Devolvemos un micro-fragmento HTML para confirmar el guardado
            return HttpResponse('<span class="text-green-500 font-bold ml-2 text-sm fade-out">¡Guardado!</span>')

    return HttpResponse('<span class="text-red-500 ml-2 text-sm fade-out">Error</span>', status=400)



@login_required
def lista_servicios(request):
    """Muestra el catálogo de servicios y permite crear nuevos"""
    tenant = request.user.tenant

    if request.method == 'POST':
        form = ServicioCatalogoForm(request.POST)
        if form.is_valid():
            nuevo_servicio = form.save(commit=False)
            nuevo_servicio.tenant = tenant
            nuevo_servicio.save()
            return redirect('inventario:lista_servicios')
    else:
        form = ServicioCatalogoForm()

    servicios = ServicioCatalogo.objects.filter(tenant=tenant).order_by('nombre')

    return render(request, 'inventario/lista_servicios.html', {
        'servicios': servicios,
        'form': form
    })


@login_required
def actualizar_precio_servicio(request, pk):
    """Vista HTMX para editar el precio de un servicio en línea"""
    if request.method == 'POST':
        servicio = get_object_or_404(ServicioCatalogo, id=pk, tenant=request.user.tenant)
        nuevo_precio = request.POST.get('precio_base')

        if nuevo_precio:
            servicio.precio_base = nuevo_precio
            servicio.save()
            return HttpResponse('<span class="text-green-500 font-bold ml-2 text-sm fade-out">¡Guardado!</span>')

    return HttpResponse('<span class="text-red-500 ml-2 text-sm fade-out">Error</span>', status=400)


@login_required
def buscar_inventario_global(request):
    """Vista HTMX para el buscador rápido de la barra superior"""
    query = request.GET.get('q', '').strip()

    if query:
        # Buscamos por nombre o código de barras, limitando a 5 para no hacer un menú gigante
        resultados = ItemInventario.objects.filter(
            Q(nombre__icontains=query) | Q(codigo_barras__icontains=query),
            sucursal=request.user.sucursal
        )[:5]

        return render(request, 'inventario/partials/resultados_globales.html', {
            'resultados': resultados,
            'query': query
        })

    # Si el input está vacío, devolvemos nada para que el menú flotante desaparezca
    return HttpResponse('')

