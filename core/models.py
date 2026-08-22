# core/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser


class Tenant(models.Model):
    """El dueño del taller de bicicletas (Cliente del SaaS)"""
    nombre = models.CharField(max_length=150)
    subdominio = models.CharField(max_length=50, unique=True)
    rfc = models.CharField(max_length=20, blank=True)
    activo = models.BooleanField(default=True)
    modulo_citas = models.BooleanField(default=False, help_text="¿Paga el módulo de agenda/citas?")
    modulo_inventario_avanzado = models.BooleanField(default=False, help_text="¿Paga control de stock y proveedores?")
    modulo_facturacion = models.BooleanField(default=False, help_text="¿Paga facturación electrónica?")
    modulo_retencion = models.BooleanField(default=False, help_text="CRM de recompras automáticas")
    modulo_garantias = models.BooleanField(default=False, help_text="Detección automática de garantías")
    modulo_punto_venta = models.BooleanField(default=False, help_text="Acceso a la app de escritorio")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre


class Sucursal(models.Model):
    """Ubicaciones físicas bajo un mismo Tenant"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='sucursales')
    nombre = models.CharField(max_length=100)
    direccion = models.TextField()
    telefono = models.CharField(max_length=20, blank=True)
    dias_garantia_servicio = models.IntegerField(default=30)
    dias_para_recordatorio = models.IntegerField(default=180)
    activa = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.tenant.nombre} - {self.nombre}"


class User(AbstractUser):
    """Usuario personalizado extendido"""
    ROLE_CHOICES = [
        ('ADMIN', 'Administrador / Dueño'),
        ('CAJERO', 'Cajero / Recepción'),
        ('TECNICO', 'Mecánico / Técnico'),
    ]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True, blank=True)
    rol = models.CharField(max_length=15, choices=ROLE_CHOICES, default='TECNICO')

    def __str__(self):
        return f"{self.username} ({self.get_rol_display()})"


class BotSession(models.Model):
    """Vincula a un mecánico con su chat de Telegram/WhatsApp para el bot interno"""
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, limit_choices_to={'rol': 'TECNICO'})
    plataforma = models.CharField(max_length=20, choices=[('TELEGRAM', 'Telegram'), ('WHATSAPP', 'WhatsApp')])
    chat_id = models.CharField(max_length=100, unique=True)
    activo = models.BooleanField(default=True)