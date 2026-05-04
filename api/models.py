from django.db import models


class TruckStop(models.Model):
    opis_truckstop_id = models.IntegerField(db_index=True)
    truckstop_name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=128)
    state = models.CharField(max_length=2, db_index=True)
    rack_id = models.IntegerField(null=True, blank=True, db_index=True)

    retail_price = models.DecimalField(max_digits=6, decimal_places=3, db_index=True)

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'opis_truckstop_id',
                    'truckstop_name',
                    'address',
                    'city',
                    'state',
                    'rack_id',
                ],
                name='uniq_truckstop_identity',
            )
        ]

    def __str__(self) -> str:
        return f"{self.truckstop_name} ({self.city}, {self.state})"
