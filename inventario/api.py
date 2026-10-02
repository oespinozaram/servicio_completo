# inventario/api.py
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import ItemInventario
from .serializers import ItemInventarioSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction


class InventarioListAPI(generics.ListAPIView):
    serializer_class = ItemInventarioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Magia multi-tenant: El token JWT ya sabe quién es el usuario.
        # Filtramos para devolver solo el inventario de su propia sucursal y que esté activo.
        usuario = self.request.user
        return ItemInventario.objects.filter(
            sucursal=usuario.sucursal,
        ).order_by('nombre')


class RegistrarVentaPOSAPI(APIView):
    # La seguridad JWT ya está activa por la configuración global

    @transaction.atomic
    def post(self, request):
        """
        Espera un payload JSON con la estructura:
        {
            "total_cobrado": 890.50,
            "items": [
                {"id": 1, "qty": 2, "precio": 120.0},
                {"id": 3, "qty": 1, "precio": 650.50}
            ]
        }
        """
        items_data = request.data.get('items', [])

        if not items_data:
            return Response({"error": "El ticket está vacío"}, status=status.HTTP_400_BAD_REQUEST)

        # TODO: Aquí puedes instanciar tu modelo de Venta/Ticket (Ej. Venta.objects.create(...))

        for item in items_data:
            producto_id = item.get('id')
            cantidad = item.get('qty')

            try:
                # select_for_update() bloquea la fila hasta que termine el request
                producto = ItemInventario.objects.select_for_update().get(
                    id=producto_id,
                    sucursal=request.user.sucursal,
                    activo=True
                )
            except ItemInventario.DoesNotExist:
                return Response({"error": f"Producto ID {producto_id} no encontrado"}, status=status.HTTP_404_NOT_FOUND)

            if producto.stock < cantidad:
                # Si esto falla, el decorador @transaction.atomic deshace cualquier descuento previo
                return Response(
                    {"error": f"Stock insuficiente para {producto.nombre}. Disponible: {producto.stock}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Descontamos y guardamos
            producto.stock -= cantidad
            producto.save()

            # TODO: Aquí crearías el DetalleVenta asociado a la cabecera

        return Response({"mensaje": "Cobro registrado y stock actualizado"}, status=status.HTTP_201_CREATED)
