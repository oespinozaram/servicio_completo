from django import forms
from .models import OrdenTrabajo, Cita
from clientes.models import Bicicleta
from core.models import User
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model


Usuario = get_user_model()


class EmpleadoForm(forms.ModelForm):
    # Añadimos un campo explícito para la contraseña
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'w-full rounded border-gray-300 p-2 border'}),
        required=True,
        label="Contraseña temporal"
    )

    class Meta:
        model = Usuario
        fields = ['username', 'first_name', 'last_name', 'email', 'rol']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'w-full rounded border-gray-300 p-2 border'}),
            'first_name': forms.TextInput(attrs={'class': 'w-full rounded border-gray-300 p-2 border'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full rounded border-gray-300 p-2 border'}),
            'email': forms.EmailInput(attrs={'class': 'w-full rounded border-gray-300 p-2 border'}),
            'rol': forms.Select(attrs={'class': 'w-full rounded border-gray-300 p-2 border bg-white'}),
        }


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
        # Añadimos 'bicicleta' a los fields
        fields = ['bicicleta', 'nombre_cliente', 'telefono', 'asunto', 'fecha', 'hora']
        widgets = {
            # Campo oculto con ID específico para nuestro buscador
            'bicicleta': forms.HiddenInput(attrs={'id': 'id_bicicleta'}),

            # Les ponemos IDs específicos para poder rellenarlos con JavaScript
            'nombre_cliente': forms.TextInput(
                attrs={'id': 'id_nombre_cliente', 'class': 'w-full rounded border-gray-300 p-2 border',
                       'placeholder': 'Nombre del cliente'}),
            'telefono': forms.TextInput(
                attrs={'id': 'id_telefono', 'class': 'w-full rounded border-gray-300 p-2 border',
                       'placeholder': 'Ej. 555-1234'}),
            'asunto': forms.TextInput(
                attrs={'class': 'w-full rounded border-gray-300 p-2 border', 'placeholder': '¿Qué servicio necesita?'}),
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded border-gray-300 p-2 border'}),
            'hora': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full rounded border-gray-300 p-2 border'}),
        }

    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop('tenant', None)
        self.sucursal = kwargs.pop('sucursal', None)
        super().__init__(*args, **kwargs)

        # La bicicleta no es obligatoria (para permitir clientes rápidos)
        self.fields['bicicleta'].required = False

        if self.tenant:
            self.fields['bicicleta'].queryset = Bicicleta.objects.filter(cliente__tenant=self.tenant)

    def clean(self):
        cleaned_data = super().clean()
        fecha = cleaned_data.get('fecha')
        hora = cleaned_data.get('hora')

        if fecha and hora and self.sucursal:
            # Contamos cuántas citas hay ese mismo día, a esa misma hora, en esta sucursal
            citas_existentes = Cita.objects.filter(
                sucursal=self.sucursal,
                fecha=fecha,
                hora=hora,
                estado='PENDIENTE'  # Solo contamos las que aún van a llegar
            ).count()

            # LÍMITE DE CAPACIDAD: (Por ahora lo ponemos en 2, luego podrías leerlo desde el modelo Sucursal)
            LIMITE_POR_HORA = 2

            if citas_existentes >= LIMITE_POR_HORA:
                # Si se superó, lanzamos un error y detenemos el guardado
                raise ValidationError(
                    f"¡Horario saturado! Ya tenemos {citas_existentes} citas agendadas para las {hora.strftime('%H:%M')} hrs. Por favor, elige otro horario.")

        return cleaned_data
