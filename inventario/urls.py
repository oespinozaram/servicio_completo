from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('', views.lista_inventario, name='lista'),
    path('item/<int:pk>/stock/', views.actualizar_stock, name='actualizar_stock'),
    path('servicios/', views.lista_servicios, name='lista_servicios'),
    path('servicios/<int:pk>/precio/', views.actualizar_precio_servicio, name='actualizar_precio_servicio'),
    path('buscar-global/', views.buscar_inventario_global, name='buscar_global'),
    path('proveedores/', views.gestion_proveedores, name='proveedores'),
    path('compras/', views.lista_compras, name='lista_compras'),
]