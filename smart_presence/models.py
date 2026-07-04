from django.db import models

class BeaconLog(models.Model):
    mac = models.CharField(max_length=17, db_index=True)
    rssi = models.IntegerField()
    raw_data = models.TextField(blank=True)
    is_ibeacon = models.BooleanField(default=False)
    uuid = models.CharField(max_length=36, blank=True, null=True, db_index=True)
    major = models.IntegerField(blank=True, null=True)
    minor = models.IntegerField(blank=True, null=True)
    device_timestamp = models.CharField(max_length=30, blank=True, null=True)
    
    # 🔥 NEW FIELD: Capture the boolean flag sent by the ESP32
    flag = models.BooleanField(null=True, blank=True, default=False)
    
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.mac} | RSSI: {self.rssi} | Flag: {self.flag} | {self.timestamp}"