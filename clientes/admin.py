from django.contrib import admin
from .models import Cliente, Bicicleta

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tenant', 'email', 'telefono', 'puntos_lealtad')
    search_fields = ('nombre', 'email', 'telefono', 'tenant__nombre')
    list_filter = ('tenant',)

@admin.register(Bicicleta)
class BicicletaAdmin(admin.ModelAdmin):
    list_display = ('marca', 'modelo', 'n_serie', 'tipo', 'cliente')
    search_fields = ('marca', 'modelo', 'n_serie', 'cliente__nombre')
    list_filter = ('tipo', 'cliente__tenant')
