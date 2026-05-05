from django.urls import re_path

from .views import ApiIndexView, FuelRoutePlanView, HealthView, RoutePlanView

urlpatterns = [
    re_path(r'^$', ApiIndexView.as_view(), name='api-index'),
    re_path(r'^health/?$', HealthView.as_view(), name='health'),
    re_path(r'^route/?$', RoutePlanView.as_view(), name='route-plan'),
    re_path(r'^fuel-routes/?$', FuelRoutePlanView.as_view(), name='fuel-routes'),
]
