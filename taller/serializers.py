from rest_framework import serializers
from .models import OrdenTrabajo, DetalleOrdenServicio


class DetalleOrdenServicioSerializer(serializers.ModelSerializer):
    # Asumo que ServicioCatalogo tiene un campo 'nombre'
    concepto = serializers.CharField(source='servicio.nombre', read_only=True)

    class Meta:
        model = DetalleOrdenServicio
        fields = ['id', 'concepto', 'precio_aplicado']


class OrdenTrabajoSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)
    bicicleta_info = serializers.CharField(source='bicicleta.marca', read_only=True)

    # Anidamos los servicios usando tu related_name='servicios'
    servicios = DetalleOrdenServicioSerializer(many=True, read_only=True)

    # Exponemos tu @property total_orden
    total = serializers.DecimalField(source='total_orden', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrdenTrabajo
        fields = [
            'id', 'uuid_publico', 'cliente_nombre', 'bicicleta_info',
            'estado', 'pagada', 'total', 'servicios'
        ]