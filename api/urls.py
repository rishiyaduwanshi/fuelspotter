from django.urls import path

from .views import ApiIndexView, HealthView, RoutePlanView

urlpatterns = [
    path('', ApiIndexView.as_view(), name='api-index'),
    path('health/', HealthView.as_view(), name='health'),
    path('route/', RoutePlanView.as_view(), name='route-plan'),
]
