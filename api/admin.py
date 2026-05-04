from django.contrib import admin

from .models import TruckStop


@admin.register(TruckStop)
class TruckStopAdmin(admin.ModelAdmin):
    list_display = (
        'truckstop_name',
        'city',
        'state',
        'retail_price',
        'opis_truckstop_id',
        'rack_id',
    )
    list_filter = ('state',)
    search_fields = ('truckstop_name', 'city', 'address', 'opis_truckstop_id')
