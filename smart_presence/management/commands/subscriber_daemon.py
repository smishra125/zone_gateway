# smart_presence/management/commands/subscriber_daemon.py
import json
from django.core.management.base import BaseCommand
import paho.mqtt.client as mqtt
from smart_presence.models import BeaconLog

MQTT_BROKER = "127.0.0.1"
MQTT_PORT = 1883
MQTT_TOPIC = "esp32s3/beacons"

def parse_ibeacon_signature(hex_str):
    """
    Parses raw advertising hexadecimal payloads to match Apple's 
    iBeacon signature block (Company ID: 4c00 + Indicator: 0215).
    """
    try:
        if len(hex_str) >= 58 and "4c000215" in hex_str:
            # Locate position offsets of the header signature block
            idx = hex_str.index("4c000215")
            
            # Slice and structure the 16-Byte UUID string
            u_start = idx + 8
            u_str = hex_str[u_start : u_start + 32]
            uuid = f"{u_str[0:8]}-{u_str[8:12]}-{u_str[12:16]}-{u_str[16:20]}-{u_str[20:32]}".upper()
            
            # Slice Big-Endian Major and Minor values
            major = int(hex_str[u_start + 32 : u_start + 36], 16)
            minor = int(hex_str[u_start + 36 : u_start + 40], 16)
            
            return True, uuid, major, minor
    except Exception:
        pass
    return False, None, None, None

def on_connect(client, userdata, flags, rc):
    print(f"Connected to Mosquitto Broker at [{MQTT_BROKER}:{MQTT_PORT}]")
    client.subscribe(MQTT_TOPIC)
    print(f"Listening for incoming ESP32-S3 beacon data stream on '{MQTT_TOPIC}'...")

def on_message(client, userdata, msg):
    try:
        # Step A: Parse string input to JSON object
        payload = json.loads(msg.payload.decode('utf-8'))
        mac_addr = payload.get('mac')
        rssi_val = payload.get('rssi')
        raw_hex = payload.get('data', '')

        # Step B: Identify and parse embedded packet telemetry profiles
        is_ibeacon, uuid, major, minor = parse_ibeacon_signature(raw_hex)

        # Step C: Save data entries securely using Django ORM
        log_entry = BeaconLog.objects.create(
            mac=mac_addr,
            rssi=rssi_val,
            raw_data=raw_hex,
            is_ibeacon=is_ibeacon,
            uuid=uuid,
            major=major,
            minor=minor
        )

        # Output readable status reports to terminal console
        print(f"[{log_entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] Saved Beacon Entry:")
        print(f"  🔹 MAC Address   : {mac_addr}")
        print(f"  🔹 RSSI Signal   : {rssi_val} dBm")
        if is_ibeacon:
            print(f"  🔹 UUID Location : {uuid}")
            print(f"  🔹 Major Zone ID : {major} | Minor Room ID: {minor}")
        print("-" * 60)

    except Exception as e:
        print(f"Inbound processing breakdown encountered: {e}")

class Command(BaseCommand):
    help = 'Starts the long-running daemon task absorbing raw MQTT stream packets into Django DB.'

    def handle(self, *args, **options):
        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message

        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        # Block and preserve execution context indefinitely
        client.loop_forever()