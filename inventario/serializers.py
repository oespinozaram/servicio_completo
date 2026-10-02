from rest_framework import serializers
from .models import ItemInventario # Ajusta si tu modelo tiene otro nombre


class ItemInventarioSerializer(serializers.ModelSerializer):
    # Si la categoría es una llave foránea, esto extrae el texto directo para facilitar el trabajo en Flet
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True, default="General")

    class Meta:
        model = ItemInventario
        fields = [
            'id',
            'nombre',
            'precio_venta',
            'stock',
            'categoria_nombre'
        ]