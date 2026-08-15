# clientes/urls.py
from django.urls import path
from . import views

app_name = 'clientes'

urlpatterns = [
    path('', views.directorio_clientes, name='directorio'),
    path('perfil/<int:pk>/', views.perfil_cliente, name='perfil'),
    path('nuevo/', views.nuevo_cliente_bici, name='nuevo_cliente_bici'),
]