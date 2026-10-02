from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from .models import OrdenTrabajo
from .serializers import OrdenTrabajoSerializer


class OrdenesListasAPI(generics.ListAPIView):
    """Devuelve las órdenes que están listas para entrega y no han sido pagadas."""
    serializer_class = OrdenTrabajoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OrdenTrabajo.objects.filter(
            sucursal=self.request.user.sucursal,
            estado='REPARADA',
            pagada=False
        ).order_by('-updated_at')


class OrdenDetalleAPI(generics.RetrieveAPIView):
    """Devuelve la orden específica para pintar el ticket de cobro."""
    serializer_class = OrdenTrabajoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OrdenTrabajo.objects.filter(sucursal=self.request.user.sucursal)


class CobrarOrdenAPI(APIView):
    """Procesa el pago, marca como pagada y cambia a estado ENTREGADA."""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        try:
            orden = OrdenTrabajo.objects.select_for_update().get(
                pk=pk,
                sucursal=request.user.sucursal,
                estado='REPARADA',
                pagada=False
            )
        except OrdenTrabajo.DoesNotExist:
            return Response(
                {"error": "Orden no encontrada, en otro estado o ya fue pagada."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Actualizamos estado según tus STATUS_CHOICES
        orden.estado = 'ENTREGADA'
        orden.pagada = True
        orden.save()

        return Response(
            {"mensaje": f"Orden #{orden.id} cobrada exitosamente"},
            status=status.HTTP_200_OK
        )