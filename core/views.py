from django.shortcuts import render, redirect
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy


def landing_page(request):
    """Página de inicio pública (Marketing y Login)"""
    # Si el usuario ya inició sesión, no tiene caso mostrarle la página de ventas,
    # lo mandamos directo a su panel de control.
    if request.user.is_authenticated:
        return redirect('taller:dashboard')

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
        return reverse_lazy('taller:dashboard')
