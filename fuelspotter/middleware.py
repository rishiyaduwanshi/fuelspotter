from __future__ import annotations

from django.http import JsonResponse


class ApiJson404Middleware:
    """Return JSON 404s for /api/* paths.

    Django's default 404 in DEBUG mode is HTML. This middleware normalizes
    API 404 responses to JSON regardless of DEBUG.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if not request.path.startswith('/api/'):
            return response

        if response.status_code != 404:
            return response

        content_type = (response.get('Content-Type') or '').lower()
        if 'application/json' in content_type:
            return response

        return JsonResponse(
            {
                'error': 'Not Found',
                'path': request.path,
            },
            status=404,
        )
