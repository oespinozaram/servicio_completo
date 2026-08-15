# taller/models.py
from django.db import models
from core.models import Sucursal, User
from clientes.models import Cliente, Bicicleta
from inventario.models import ServicioCatalogo, ItemInventario
import secrets


def generar_token_publico():
    return secrets.token_urlsafe(16)


class OrdenTrabajo(models.Model):
    STATUS_CHOICES = [
        ('RECIBIDA', 'Recibida'),
        ('DIAGNOSTICO', 'En Diagnóstico'),
        ('REPARACION', 'En Reparación'),
        ('LISTA', 'Lista para Entrega'),
        ('ENTREGADA', 'Entregada'),
    ]
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    bicicleta = models.ForeignKey(Bicicleta, on_delete=models.PROTECT)
    tecnico = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                limit_choices_to={'rol': 'TECNICO'})

    estado = models.CharField(max_length=15, choices=STATUS_CHOICES, default='RECIBIDA')
    notas_cliente = models.TextField(blank=True, help_text="Problema reportado por el cliente")
    notas_internas = models.TextField(blank=True, help_text="Notas privadas del mecánico")

    token_publico = models.CharField(max_length=64, unique=True, default=generar_token_publico)
    pagada = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Orden #{self.id} - {self.bicicleta.marca} ({self.estado})"

    @property
    def total_orden(self):
        """Calcula la suma de piezas, servicios y cargos aplicados a la orden"""
        total_servicios = sum(detalle.precio_aplicado for detalle in self.servicios.all())
        total_piezas = sum(detalle.precio_aplicado * detalle.cantidad for detalle in self.piezas.all())
        total_cargos = sum(cargo.subtotal for cargo in self.cargos.all())
        return total_servicios + total_piezas + total_cargos


class DetalleOrdenServicio(models.Model):
    orden = models.ForeignKey(OrdenTrabajo, on_delete=models.CASCADE, related_name='servicios')
    servicio = models.ForeignKey(ServicioCatalogo, on_delete=models.PROTECT)
    precio_aplicado = models.DecimalField(max_digits=10, decimal_places=2)


class DetalleOrdenPieza(models.Model):
    orden = models.ForeignKey(OrdenTrabajo, on_delete=models.CASCADE, related_name='piezas')
    item = models.ForeignKey(ItemInventario, on_delete=models.PROTECT)
    cantidad = models.IntegerField(default=1)
    precio_aplicado = models.DecimalField(max_digits=10, decimal_places=2)


class HistorialEstado(models.Model):
    orden = models.ForeignKey(OrdenTrabajo, on_delete=models.CASCADE, related_name='historial')
    estado_anterior = models.CharField(max_length=15)
    estado_nuevo = models.CharField(max_length=15)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)


class Pago(models.Model):
    METODO_CHOICES = [
        ('EFECTIVO', 'Efectivo'),
        ('TARJETA', 'Tarjeta de Crédito / Débito'),
        ('TRANSFERENCIA', 'Transferencia (SPEI)'),
    ]
    orden = models.ForeignKey(OrdenTrabajo, on_delete=models.CASCADE, related_name='pagos')
    cajero = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, help_text="Usuario que cobró")
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    metodo = models.CharField(max_length=20, choices=METODO_CHOICES, default='EFECTIVO')
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pago de ${self.monto} para Orden #{self.orden.id}"


class Cita(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('ATENDIDA', 'Atendida (En Taller)'),
        ('CANCELADA', 'Cancelada'),
    ]

    sucursal = models.ForeignKey('core.Sucursal', on_delete=models.CASCADE, related_name='citas')
    nombre_cliente = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20)
    asunto = models.CharField(max_length=150, help_text="Ej. Mantenimiento general, cambio de llantas...")
    fecha = models.DateField()
    hora = models.TimeField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha', 'hora']  # Para que siempre salgan en orden cronológico

    def __str__(self):
        return f"{self.fecha} - {self.nombre_cliente}"


class CargoOrden(models.Model):
    # Relación: A qué orden pertenece este renglón.
    # El related_name='cargos' nos permitirá hacer cosas como: orden.cargos.all()
    orden = models.ForeignKey(OrdenTrabajo, on_delete=models.CASCADE, related_name='cargos')

    # Descripción del cargo (ej. "Lavado General", "Cadena Shimano")
    descripcion = models.CharField(max_length=200)

    # Cantidad y precio unitario
    cantidad = models.PositiveIntegerField(default=1)
    precio = models.DecimalField(max_digits=10, decimal_places=2, help_text="Precio unitario")

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def subtotal(self):
        """Calcula el total de este renglón (cantidad * precio)"""
        return self.cantidad * self.precio

    def __str__(self):
        return f"{self.cantidad}x {self.descripcion} - ${self.subtotal}"
