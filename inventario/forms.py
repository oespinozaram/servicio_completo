from django import forms
from .models import ItemInventario, ServicioCatalogo, Proveedor


class ItemInventarioForm(forms.ModelForm):
    class Meta:
        model = ItemInventario
        fields = ['nombre', 'codigo_barras', 'precio_costo', 'precio_venta', 'stock', 'ubicacion_pasillo',
                  'ubicacion_cajon']

        # Estilos base de Tailwind
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'w-full rounded border-gray-300 p-2 border'}),
            'codigo_barras': forms.TextInput(attrs={'class': 'w-full rounded border-gray-300 p-2 border'}),
            'precio_costo': forms.NumberInput(attrs={'class': 'w-full rounded border-gray-300 p-2 border'}),
            'precio_venta': forms.NumberInput(attrs={'class': 'w-full rounded border-gray-300 p-2 border'}),
            'stock': forms.NumberInput(attrs={'class': 'w-full rounded border-gray-300 p-2 border'}),
            'ubicacion_pasillo': forms.TextInput(attrs={'class': 'w-full rounded border-gray-300 p-2 border'}),
            'ubicacion_cajon': forms.TextInput(attrs={'class': 'w-full rounded border-gray-300 p-2 border'}),
        }

    def __init__(self, *args, **kwargs):
        # Extraemos la sucursal antes de inicializar el formulario
        sucursal = kwargs.pop('sucursal', None)
        super().__init__(*args, **kwargs)

        if sucursal:
            self.fields['proveedor_principal'].queryset = Proveedor.objects.filter(
                sucursal=sucursal,
                activo=True
            )
            self.fields['proveedor_principal'].empty_label = "Sin proveedor asignado"



class ServicioCatalogoForm(forms.ModelForm):
    class Meta:
        model = ServicioCatalogo
        fields = ['nombre', 'descripcion', 'precio_base']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'w-full rounded border-gray-300 p-2 border', 'placeholder': 'Ej. Lavado General'}),
            'descripcion': forms.Textarea(attrs={'class': 'w-full rounded border-gray-300 p-2 border', 'rows': 2, 'placeholder': 'Desengrasado, lavado y lubricación...'}),
            'precio_base': forms.NumberInput(attrs={'class': 'w-full rounded border-gray-300 p-2 border'}),
        }
