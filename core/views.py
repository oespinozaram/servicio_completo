from django.shortcuts import render, redirect
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.urls import reverse_lazy
from .models import Prospecto
from django.views.generic.base import TemplateView


def landing_page(request):
    """Página de inicio pública (Marketing y Login)"""
    # Si el usuario ya inició sesión, no tiene caso mostrarle la página de ventas,
    # lo mandamos directo a su panel de control.
    if request.user.is_authenticated:
        return redirect('taller:dashboard_inicio')

    return render(request, 'core/landing.html')


class LoginInteligenteView(LoginView):
    # Asegúrate de poner el nombre exacto de tu plantilla de login
    template_name = 'login.html'

    def get_success_url(self):
        usuario = self.request.user

        # Si es mecánico, su mundo es el tablero de trabajo
        if usuario.rol == 'TECNICO':
            return reverse_lazy('taller:kanban')

        # Si es Dueño o Cajero, necesitan ver los números y el CRM
        return reverse_lazy('taller:dashboard_inicio')


def solicitar_demo(request):
    """Captura el formulario de la landing y guarda el prospecto."""
    if request.method == 'POST':
        nombre_taller = request.POST.get('nombre_taller', '').strip()
        telefono = request.POST.get('telefono', '').strip()

        if nombre_taller and telefono:
            Prospecto.objects.create(
                nombre_taller=nombre_taller,
                telefono=telefono,
            )
            messages.success(
                request,
                f'¡Gracias, {nombre_taller}! Te contactaremos pronto para agendar tu demo. 🚲'
            )

    # Tanto en éxito como en GET directo, redirigimos a la landing
    return redirect('landing_page')


class LegalView(TemplateView):
    template_name = 'legal.html'
