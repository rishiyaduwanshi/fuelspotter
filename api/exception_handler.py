from __future__ import annotations

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def custom_exception_handler(exc: Exception, context):
    """Ensure API endpoints always return JSON.

    DRF only converts known exception types to Response. For unexpected
    exceptions (e.g. RuntimeError), the default is to re-raise which becomes
    Django's HTML debug page in DEBUG.
    """

    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    # Domain errors → 400.
    try:
        from api.services.fuel_planner import FuelPlanningError

        if isinstance(exc, FuelPlanningError):
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        # Avoid hard failure if imports change.
        pass

    data = {
        'error': str(exc) or 'Server Error',
    }
    if settings.DEBUG:
        data['type'] = exc.__class__.__name__

    return Response(data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
