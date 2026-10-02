from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class TallerConfigAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant = request.user.tenant
        return Response({
            "nombre_comercial": tenant.nombre,
            "direccion": "Av. Insurgentes 123, Tepic, Nayarit", # O tenant.direccion si lo tienes en BD
            "telefono": "311-555-0000", # O tenant.telefono
            "mensaje_ticket": "¡Gracias por rodar con nosotros!"
        })
