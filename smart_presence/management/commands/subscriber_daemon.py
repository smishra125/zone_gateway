# smart_presence/management/commands/subscriber_daemon.py
import json
from django.core.management.base import BaseCommand
import paho.mqtt.client as mqtt
from smart_presence.models import BeaconLog

MQTT_BROKER = "127.0.0.1"
MQTT_PORT = 1883
MQTT_TOPIC = "esp32s3/beacons"

def on_connect(client, userdata, flags, rc):
    print(f"Connected to Mosquitto Broker at [{MQTT_BROKER}:{MQTT_PORT}]")
    client.subscribe(MQTT_TOPIC)
    print(f"Listening for incoming multi-gateway beacon data stream on '{MQTT_TOPIC}'...")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        
        #  EXTRACT THE NEW SCANNER ID HERE
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

        # Save to database incorporating the new scanner identity field
        log_entry = BeaconLog.objects.create(
            scanner_id=sc_id,  # <-- Map it here!
            mac=mac_addr,
            rssi=rssi_val,
            raw_data=raw_hex,
            is_ibeacon=is_ibeacon,
            uuid=uuid.upper() if uuid else None,
            major=major,
            minor=minor,
            device_timestamp=esp_timestamp,
            flag=beacon_flag
        )

        # Output readable status tracking reports to terminal console
        print(f"[{log_entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] Saved Beacon Entry:")
        print(f"  🏢 Gateway Identity: {sc_id}")  # <-- Visually track it in console
        print(f"  🔹 ESP Hardware Time: {esp_timestamp}")
        print(f"  🔹 MAC Address   : {mac_addr}")
        print(f"  🔹 RSSI Signal   : {rssi_val} dBm")
        print(f"  🔹 Type          : {pkt_type}")
        print(f"  🔹 Status Flag   : {beacon_flag}")
        if is_ibeacon:
            print(f"  🔹 UUID Location : {uuid.upper() if uuid else 'N/A'}")
            print(f"  🔹 Major Zone ID : {major} | Minor Room ID: {minor}")
        print("-" * 60)

    except Exception as e:
        print(f"Inbound processing breakdown encountered: {e}")

class Command(BaseCommand):
    help = 'Starts the long-running daemon task absorbing multi-scanner MQTT stream packets into Django DB.'

    def handle(self, *args, **options):
        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message

        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
