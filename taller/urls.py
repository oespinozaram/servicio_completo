from django.urls import path
from . import views

app_name = 'taller'

urlpatterns = [
    path('', views.dashboard_inicio, name='dashboard'),
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
    path('rastreo/<str:token>/', views.rastreo_publico, name='rastreo_publico'),
    path('agenda/', views.agenda_citas, name='agenda'),
    path('agenda/<int:pk>/atendida/', views.marcar_cita_atendida, name='marcar_cita_atendida'),
    path('corte-caja/', views.corte_caja, name='corte_caja'),
]