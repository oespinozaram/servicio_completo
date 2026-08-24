from django.urls import path
from . import views

app_name = 'taller'

urlpatterns = [
    path('', views.dashboard_inicio, name='dashboard_inicio'),
    path('kanban/', views.tablero_kanban, name='kanban'),
    path('nueva/', views.nueva_orden, name='nueva_orden'),
    path('buscar-bicicletas/', views.buscar_bicicletas, name='buscar_bicicletas'),
    path('orden/<int:pk>/', views.detalle_orden, name='detalle_orden'),
    path('orden/<int:pk>/estado/<str:nuevo_estado>/', views.cambiar_estado_orden, name='cambiar_estado_orden'),
    path('orden/<int:pk>/buscar-cargos/', views.buscar_cargos, name='buscar_cargos'),
    path('orden/<int:pk>/agregar-cargo/', views.agregar_cargo, name='agregar_cargo'),
    path('cargo/<int:cargo_id>/eliminar/', views.eliminar_cargo, name='eliminar_cargo'),
    path('orden/<int:pk>/agregar-servicio/<int:servicio_id>/', views.agregar_servicio, name='agregar_servicio'),
    path('orden/<int:pk>/agregar-pieza/<int:pieza_id>/', views.agregar_pieza, name='agregar_pieza'),
    path('orden/<int:pk>/cobrar/', views.cobrar_orden, name='cobrar_orden'),
    path('rastreo/<uuid:token>/', views.rastreo_publico, name='rastreo_publico'),
    path('agenda/', views.agenda_citas, name='agenda'),
    path('cita/<int:pk>/recibir/', views.recibir_cita, name='recibir_cita'),
    path('agenda/<int:pk>/atendida/', views.marcar_cita_atendida, name='marcar_cita_atendida'),
    path('orden/<int:pk>/asignar-tecnico/', views.asignar_tecnico, name='asignar_tecnico'),
    path('corte-caja/', views.corte_caja, name='corte_caja'),
    path('orden/<int:pk>/imprimir/', views.imprimir_ticket, name='imprimir_ticket'),
    path('orden/<int:pk>/whatsapp/', views.notificar_whatsapp, name='notificar_whatsapp'),
    path('orden/<int:pk>/avanzar/', views.avanzar_estado_orden, name='avanzar_estado_orden'),
    path('dashboard/', views.dashboard_analitico, name='dashboard_analitico'),
    path('personal/', views.gestion_personal, name='gestion_personal'),
    path('personal/<int:pk>/editar/', views.editar_empleado, name='editar_empleado'),
    path('personal/<int:pk>/toggle-estado/', views.toggle_estado_empleado, name='toggle_estado_empleado'),
    path('orden/<int:pk>/agregar-evidencia/', views.agregar_cargo_evidencia, name='agregar_cargo_evidencia'),
    path('orden/<int:pk>/inspeccion/', views.inspeccion_mecanico, name='inspeccion_mecanico'),
    path('rastreo/<uuid:token>/respuesta/<str:accion>/', views.responder_aprobacion, name='responder_aprobacion'),
    path('retencion/', views.panel_retencion, name='panel_retencion'),
    path('retencion/<int:pk>/marcar/', views.marcar_recordatorio, name='marcar_recordatorio'),
    path('orden/<int:pk>/subir-evidencia/', views.subir_evidencia, name='subir_evidencia'),
]