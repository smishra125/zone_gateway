# smart_presence/management/commands/subscriber_daemon.py
import json
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.db.models import Avg
import paho.mqtt.client as mqtt
from smart_presence.models import BeaconLog

MQTT_BROKER = "127.0.0.1"
MQTT_PORT = 1883
MQTT_TOPIC = "esp32s3/beacons"

def calculate_assigned_location(mac_address, current_esp_time_str):
    """
    Localization Engine:
    Looks at all logs for this MAC address within a tight 10-second window
    and averages the RSSI per scanner. The scanner with the highest average wins.
    """
    try:
        # Parse the ISO timestamp sent by the ESP32
        # Example format: "2026-07-08T21:05:09"
        target_time = datetime.strptime(current_esp_time_str.split('.')[0], "%Y-%m-%dT%H:%M:%S")
        
        # Look 5 seconds backward and 5 seconds forward around this packet's hardware timestamp
        start_window = target_time - timedelta(seconds=5)
        end_window = target_time + timedelta(seconds=5)
        
        # Convert to strings for simple CharField range matching or fallback to insertion time
        # For reliability, we query using our Django database auto-timestamp window:
        logs_in_window = BeaconLog.objects.filter(
            mac=mac_address,
            timestamp__gte=datetime.now() - timedelta(seconds=10) # 10-second rolling server history
        )
        
        if not logs_in_window.exists():
            return "Unknown (Insufficient Data)"
            
        # Group metrics by scanner_id and calculate the Average RSSI
        scanner_averages = (
            logs_in_window.values('scanner_id')
            .annotate(avg_rssi=Avg('rssi'))
            .order_by('-avg_rssi') # Highest average RSSI (closest to 0) comes first
        )
        
        if scanner_averages:
            winning_scanner = scanner_averages[0]['scanner_id']
            winning_rssi = scanner_averages[0]['avg_rssi']
            return winning_scanner
            
    except Exception as calc_error:
        print(f"Localization engine error: {calc_error}")
        
    return "Processing Error"

def on_connect(client, userdata, flags, rc):
    print(f"Connected to Mosquitto Broker at [{MQTT_BROKER}:{MQTT_PORT}]")
    client.subscribe(MQTT_TOPIC)
    print(f"Listening for multi-gateway beacon streams with live localization active...")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        
        sc_id = payload.get('scanner_id', 'UNKNOWN_GATEWAY')
        mac_addr = payload.get('mac')
        rssi_val = payload.get('rssi')
        pkt_type = payload.get('type', 'Standard')
        
        is_ibeacon = (pkt_type == "iBeacon")
        uuid = payload.get('uuid')
        major = payload.get('major')
        minor = payload.get('minor')
        esp_timestamp = payload.get('timestamp') 
        beacon_flag = payload.get('flag', False) 
        raw_hex = payload.get('data', '')

        # 1. Create the base log entry to record the raw message
        log_entry = BeaconLog.objects.create(
            scanner_id=sc_id,
            mac=mac_addr,
            rssi=rssi_val,
            raw_data=raw_hex,
            is_ibeacon=is_ibeacon,
            uuid=uuid.upper() if uuid else None,
            major=major,
            minor=minor,
            device_timestamp=esp_timestamp,
            flag=beacon_flag,
            assigned_location="Calculating..."
        )

        # 2. RUN ALGORITHM: Resolve position relative to competing scanner snapshots
        detected_room = calculate_assigned_location(mac_addr, esp_timestamp)
        
        # 3. Save the calculated room back to the log entry
        log_entry.assigned_location = detected_room
        log_entry.save(update_fields=['assigned_location'])

        # Output localization telemetry reports to the terminal console
        print(f"[{log_entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] Live Ingestion & Localization:")
        print(f"  🏢 Reporting Gateway : {sc_id} (Current RSSI: {rssi_val} dBm)")
        print(f"  🔹 ESP Hardware Time : {esp_timestamp}")
        print(f"  🔹 MAC Address       : {mac_addr}")
        print(f"  📍 CALCULATED ROOM   : 🌟 {detected_room} 🌟")
        print("-" * 60)

    except Exception as e:
        print(f"Inbound processing breakdown encountered: {e}")

class Command(BaseCommand):
    help = 'Starts the long-running daemon task with live multi-scanner RSSI localization logic.'

    def handle(self, *args, **options):
        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message

        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()