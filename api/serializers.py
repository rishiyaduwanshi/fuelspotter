from rest_framework import serializers


class RoutePlanRequestSerializer(serializers.Serializer):
    start = serializers.CharField()
    end = serializers.CharField()


class RoutePlanResponseSerializer(serializers.Serializer):
    start = serializers.DictField()
    end = serializers.DictField()
    route = serializers.DictField()


class FuelRoutePlanRequestSerializer(serializers.Serializer):
    start_location = serializers.CharField()
    end_location = serializers.CharField()
    include_geometry_coordinates = serializers.BooleanField(required=False, default=False)
