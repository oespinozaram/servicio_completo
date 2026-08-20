from django.shortcuts import render, redirect


def landing_page(request):
    """Página de inicio pública (Marketing y Login)"""
    # Si el usuario ya inició sesión, no tiene caso mostrarle la página de ventas,
    # lo mandamos directo a su panel de control.
    if request.user.is_authenticated:
        return redirect('taller:dashboard')

    return render(request, 'core/landing.html')