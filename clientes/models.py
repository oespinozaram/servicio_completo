# clientes/models.py
from django.db import models
from core.models import Tenant

class Cliente(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=150)
    email = models.EmailField(blank=True, null=True)
    telefono = models.CharField(max_length=20)
    puntos_lealtad = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

class Bicicleta(models.Model):
    TIPO_CHOICES = [
        ('RUTA', 'Ruta'),
        ('MTB', 'Montaña (MTB)'),
        ('URBANA', 'Urbana / Paseo'),
        ('EBIKE', 'Eléctrica (E-Bike)'),
    ]
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='bicicletas')
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50, blank=True)
    n_serie = models.CharField(max_length=100, blank=True)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='MTB')
    notas_historicas = models.TextField(blank=True)

    def __str__(self):
        return f"{self.marca} {self.modelo} - {self.cliente.nombre}"