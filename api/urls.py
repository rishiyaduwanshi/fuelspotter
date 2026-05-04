from django.urls import path

from .views import ApiIndexView, HealthView

urlpatterns = [
    path('', ApiIndexView.as_view(), name='api-index'),
    path('health/', HealthView.as_view(), name='health'),
]
