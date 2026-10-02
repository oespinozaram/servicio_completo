"""
URL configuration for servicio_completo project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from core import views as core_views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from inventario.api import InventarioListAPI, RegistrarVentaPOSAPI
from clientes.api import ClienteListAPI
from core.api import TallerConfigAPI


urlpatterns = [
    path('', core_views.landing_page, name='landing_page'),
    path('legal/', core_views.LegalView.as_view(), name='legal'),
    path('login/', core_views.LoginInteligenteView.as_view(), name='login'),
    path('admin/', admin.site.urls),
    path('taller/', include('taller.urls')),
    path('clientes/', include('clientes.urls')),
    path('login/', auth_views.LoginView.as_view(template_name='login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('api/', include('core.urls')),
    path('inventario/', include('inventario.urls')),

    # === RUTAS DE LA API (v1) ===
    # Endpoints para iniciar sesión desde Flet
    path('api/v1/auth/login/', TokenObtainPairView.as_view(), name='api_login'),
    path('api/v1/auth/refresh/', TokenRefreshView.as_view(), name='api_refresh'),

    # Endpoint del catálogo
    path('api/v1/inventario/', InventarioListAPI.as_view(), name='api_inventario'),
    path('api/v1/ventas/', RegistrarVentaPOSAPI.as_view(), name='api_ventas_pos'),

    path('api/v1/clientes/', ClienteListAPI.as_view(), name='api_clientes'),
    path('api/v1/config/', TallerConfigAPI.as_view(), name='api_config'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

