from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RoutePlanRequestSerializer
from .services.geocoding import GeocodingError, geocode_us_place
from .services.routing import RoutingError, osrm_route_driving


class HealthView(APIView):
	authentication_classes = []
	permission_classes = []

	def get(self, request):
		return Response({'status': 'ok'})


class ApiIndexView(APIView):
	authentication_classes = []
	permission_classes = []

	def get(self, request):
		return Response(
			{
				'name': 'fuelspotter-api',
				'endpoints': {
					'health': '/api/health/',
					'route_plan': '/api/route/',
				},
			}
		)


class RoutePlanView(APIView):
	authentication_classes = []
	permission_classes = []

	def post(self, request):
		serializer = RoutePlanRequestSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		start_q = serializer.validated_data['start']
		end_q = serializer.validated_data['end']

		try:
			start = geocode_us_place(start_q)
			end = geocode_us_place(end_q)
			route = osrm_route_driving(
				start_lat=start.lat,
				start_lon=start.lon,
				end_lat=end.lat,
				end_lon=end.lon,
			)
		except (GeocodingError, RoutingError) as exc:
			return Response({'error': str(exc)}, status=400)

		return Response(
			{
				'start': {
					'query': start_q,
					'display_name': start.display_name,
					'lat': start.lat,
					'lon': start.lon,
				},
				'end': {
					'query': end_q,
					'display_name': end.display_name,
					'lat': end.lat,
					'lon': end.lon,
				},
				'route': {
					'distance_m': route.distance_m,
					'duration_s': route.duration_s,
					'geometry': route.geometry,
				},
			}
		)
