from django import forms
from .models import OrdenTrabajo, Cita
from clientes.models import Bicicleta
from core.models import User


class OrdenTrabajoForm(forms.ModelForm):
    class Meta:
        model = OrdenTrabajo
        # Solo pedimos los campos iniciales, el resto se autocompleta en la vista
        fields = ['bicicleta', 'tecnico', 'notas_cliente']

        # Le damos un poco de estilo base de Tailwind a los inputs
        widgets = {
            # Ocultamos el campo real, nuestro buscador dinámico se encargará de llenarlo
            'bicicleta': forms.HiddenInput(attrs={'id': 'id_bicicleta'}),
            'tecnico': forms.Select(attrs={
                'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 p-2 border'}),
            'notas_cliente': forms.Textarea(attrs={
                'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 p-2 border',
                'rows': 3,
                'placeholder': 'Ej. El cliente reporta un ruido extraño al pedalear fuerte...'
            }),
        }

    def __init__(self, *args, **kwargs):
        # Extraemos las variables que le pasaremos desde la vista
        sucursal = kwargs.pop('sucursal', None)
        tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)

        # Filtramos los QuerySets para respetar el Multi-Tenant
        if tenant:
            # Solo mostramos bicicletas que pertenezcan a clientes de este Tenant
            self.fields['bicicleta'].queryset = Bicicleta.objects.filter(cliente__tenant=tenant)
        if sucursal:
            # Solo mostramos usuarios que sean TÉCNICOS de esta Sucursal
            self.fields['tecnico'].queryset = User.objects.filter(sucursal=sucursal, rol='TECNICO')
            # El técnico no es obligatorio al recibir la bici, puede asignarse después
            self.fields['tecnico'].required = False


class CitaForm(forms.ModelForm):
    class Meta:
        model = Cita
        fields = ['nombre_cliente', 'telefono', 'asunto', 'fecha', 'hora']
        widgets = {
            'nombre_cliente': forms.TextInput(attrs={'class': 'w-full rounded border-gray-300 p-2 border', 'placeholder': 'Nombre del cliente'}),
            'telefono': forms.TextInput(attrs={'class': 'w-full rounded border-gray-300 p-2 border', 'placeholder': 'Ej. 555-1234'}),
            'asunto': forms.TextInput(attrs={'class': 'w-full rounded border-gray-300 p-2 border', 'placeholder': '¿Qué servicio necesita?'}),
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded border-gray-300 p-2 border'}),
            'hora': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full rounded border-gray-300 p-2 border'}),
        }
