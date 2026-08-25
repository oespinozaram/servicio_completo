from django.contrib import admin
from .models import OrdenTrabajo, DetalleOrdenServicio, DetalleOrdenPieza, HistorialEstado, Cita, Pago, Evidencia

class DetalleOrdenServicioInline(admin.TabularInline):
    model = DetalleOrdenServicio
    extra = 1

class DetalleOrdenPiezaInline(admin.TabularInline):
    model = DetalleOrdenPieza
    extra = 1

class HistorialEstadoInline(admin.TabularInline):
    model = HistorialEstado
    extra = 0
    readonly_fields = ('estado_anterior', 'estado_nuevo', 'usuario', 'changed_at')
    can_delete = False

@admin.register(OrdenTrabajo)
class OrdenTrabajoAdmin(admin.ModelAdmin):
    list_display = ('id', 'bicicleta', 'cliente', 'sucursal', 'estado', 'tecnico', 'pagada', 'created_at')
    search_fields = ('id', 'cliente__nombre', 'bicicleta__n_serie', 'bicicleta__marca', 'token_publico')
    list_filter = ('estado', 'pagada', 'sucursal', 'sucursal__tenant')
    inlines = [DetalleOrdenServicioInline, DetalleOrdenPiezaInline, HistorialEstadoInline]
    readonly_fields = ('token_publico', 'created_at', 'updated_at')

@admin.register(DetalleOrdenServicio)
class DetalleOrdenServicioAdmin(admin.ModelAdmin):
    list_display = ('orden', 'servicio', 'precio_aplicado')
    search_fields = ('orden__id', 'servicio__nombre')

@admin.register(DetalleOrdenPieza)
class DetalleOrdenPiezaAdmin(admin.ModelAdmin):
    list_display = ('orden', 'item', 'cantidad', 'precio_aplicado')
    search_fields = ('orden__id', 'item__nombre')

@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    list_display = ('orden', 'estado_anterior', 'estado_nuevo', 'usuario', 'changed_at')
    search_fields = ('orden__id', 'usuario__username')
    list_filter = ('estado_nuevo', 'changed_at')

@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ('bicicleta', 'nombre_cliente', 'sucursal', 'estado',  'estado', 'fecha', 'hora')
    search_fields = ('id', 'nombre_cliente', 'bicicleta__n_serie', 'bicicleta__marca')
    list_filter = ('estado', 'sucursal', 'sucursal__tenant')
    # inlines = [DetalleOrdenServicioInline, DetalleOrdenPiezaInline, HistorialEstadoInline]
    # readonly_fields = ( 'created_at', 'updated_at')


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('orden', 'cajero', 'metodo', 'monto', 'fecha')
    list_filter = ('metodo', 'fecha')

#admin.site.register(Pago)
@admin.register(Evidencia)
class EvidenciaAdmin(admin.ModelAdmin):
    list_display = ('orden', 'archivo', 'descripcion', 'fecha_subida')
    list_filter = ('orden',)
