# smart_presence/models.py
from django.db import models

class BeaconLog(models.Model):
    # Core fields extracted directly from your MQTT string
    mac = models.CharField(max_length=17, db_index=True)
    rssi = models.IntegerField()
    raw_data = models.TextField()
    
    # Expanded iBeacon structural data fields
    is_ibeacon = models.BooleanField(default=False)
    uuid = models.CharField(max_length=36, blank=True, null=True, db_index=True)
    major = models.IntegerField(blank=True, null=True)
    minor = models.IntegerField(blank=True, null=True)
    
    # Automatically logged timestamp for timeseries-based presence analytics
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.mac} | RSSI: {self.rssi} | {self.timestamp}"