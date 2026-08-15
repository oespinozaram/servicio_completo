from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Tenant, Sucursal, User, BotSession

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'subdominio', 'rfc', 'activo', 'created_at')
    search_fields = ('nombre', 'subdominio', 'rfc')
    list_filter = ('activo', 'created_at')

@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tenant', 'telefono', 'activa')
    search_fields = ('nombre', 'tenant__nombre')
    list_filter = ('activa', 'tenant')

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = UserAdmin.list_display + ('tenant', 'sucursal', 'rol')
    list_filter = UserAdmin.list_filter + ('tenant', 'sucursal', 'rol')
    search_fields = UserAdmin.search_fields + ('tenant__nombre', 'sucursal__nombre')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Información Multi-Tenant y Rol', {
            'fields': ('tenant', 'sucursal', 'rol'),
        }),
    )

@admin.register(BotSession)
class BotSessionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'plataforma', 'chat_id', 'activo')
    search_fields = ('usuario__username', 'chat_id')
    list_filter = ('plataforma', 'activo')
