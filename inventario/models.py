# inventario/models.py
from django.db import models
from core.models import Tenant, Sucursal


class CategoriaServicio(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class ServicioCatalogo(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    categoria = models.ForeignKey(CategoriaServicio, on_delete=models.SET_NULL, null=True)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    precio_base = models.DecimalField(max_digits=10, decimal_places=2)
    tiempo_estimado_minutos = models.IntegerField(default=30)

    def __str__(self):
        return self.nombre


class Proveedor(models.Model):
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    dias_visita = models.CharField(
        max_length=100,
        blank=True,
        help_text="Ej. Pasa los Lunes y Jueves por la mañana"
    )
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class ItemInventario(models.Model):
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    codigo_barras = models.CharField(max_length=100, blank=True, null=True)
    nombre = models.CharField(max_length=150)
    stock = models.IntegerField(default=0)
    stock_minimo = models.PositiveIntegerField(
        default=2,
        help_text="Punto de reorden: El sistema alertará cuando el stock baje de este número."
    )
    precio_costo = models.DecimalField(max_digits=10, decimal_places=2)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)
    proveedor_principal = models.ForeignKey(
        Proveedor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="productos_surtidos"
    )
    ubicacion_pasillo = models.CharField(max_length=50, blank=True)
    ubicacion_cajon = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.nombre
