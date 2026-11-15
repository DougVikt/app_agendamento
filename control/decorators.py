from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def group_required(*group_names):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(request, *args, **kwargs):
            if request.user.is_staff or request.user.groups.filter(name__in=group_names).exists():
                return view(request, *args, **kwargs)
            raise PermissionDenied
        return wrapped
    return decorator