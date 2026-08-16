# taller/decorators.py
from django.core.exceptions import PermissionDenied
from functools import wraps


def admin_requerido(view_func):
    """Decorador que rechaza a cualquier usuario que no sea ADMIN"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.rol == 'ADMIN':
            return view_func(request, *args, **kwargs)
        # Si es mecánico o recepcionista, lanzamos un error 403 Forbidden
        raise PermissionDenied("No tienes permisos para ver el módulo financiero.")
    return _wrapped_view
