from django.contrib import admin
from .models import CategoriaServicio, ServicioCatalogo, ItemInventario

@admin.register(CategoriaServicio)
class CategoriaServicioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tenant')
    search_fields = ('nombre', 'tenant__nombre')
    list_filter = ('tenant',)

@admin.register(ServicioCatalogo)
class ServicioCatalogoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'tenant', 'precio_base', 'tiempo_estimado_minutos')
    search_fields = ('nombre', 'categoria__nombre', 'tenant__nombre')
    list_filter = ('tenant', 'categoria')

@admin.register(ItemInventario)
class ItemInventarioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo_barras', 'sucursal', 'stock', 'precio_venta')
    search_fields = ('nombre', 'codigo_barras', 'sucursal__nombre', 'sucursal__tenant__nombre')
    list_filter = ('sucursal', 'sucursal__tenant')
