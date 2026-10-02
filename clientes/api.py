from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .models import Cliente


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = ['id', 'nombre', 'telefono', 'email']


class ClienteListAPI(generics.ListAPIView):
    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Filtramos por el Tenant del usuario logueado
        queryset = Cliente.objects.filter(tenant=self.request.user.tenant)
        query = self.request.query_params.get('q', None)

        if query:
            queryset = queryset.filter(Q(nombre__icontains=query) | Q(telefono__icontains=query))
        return queryset
    