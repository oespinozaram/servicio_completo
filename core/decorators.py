# core/decorators.py (o core/decorators.py)
from django.core.exceptions import PermissionDenied
from functools import wraps


def modulo_requerido(nombre_modulo):
    """
    Verifica si el Tenant actual tiene pagado/activo el módulo solicitado.
    Ejemplo de uso: @modulo_requerido('modulo_citas')
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Obtenemos el tenant del usuario actual
            tenant = request.user.tenant

            # Usamos getattr para checar el valor del campo dinámicamente
            # Si getattr(tenant, 'modulo_citas') es True, lo dejamos pasar.
            if tenant and getattr(tenant, nombre_modulo, False):
                return view_func(request, *args, **kwargs)

            raise PermissionDenied(
                "Tu suscripción actual no incluye este módulo. Contacta a soporte para mejorar tu plan.")

        return _wrapped_view

    return decorator