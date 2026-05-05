from rest_framework import serializers


class RoutePlanRequestSerializer(serializers.Serializer):
    start = serializers.CharField()
    end = serializers.CharField()


class RoutePlanResponseSerializer(serializers.Serializer):
    start = serializers.DictField()
    end = serializers.DictField()
    route = serializers.DictField()
