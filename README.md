## System Architecture

+-----------------------+      MQTT Topic       +-------------------------+
|   ESP32-S3 Gateway    | --------------------> |    Mosquitto Broker     |
| (Scans BLE Beacons)   |  "esp32s3/beacons"    |      (Port: 1883)       |
+-----------------------+                       +------------+------------+
                                                             |
                                                             | Delivers string payload
                                                             v
+-----------------------+    Django ORM Save    +-------------------------+
| Local SQLite Database | <-------------------- |  subscriber_daemon App  |
|     (db.sqlite3)      |                       | (Long-running Process)  |
+-----------------------+                       +-------------------------+


==================================================================================================================
## Directory Structure

gateway_project/                 <-- Your root project folder
│
├── manage.py                    <-- Django's main execution script
├── db.sqlite3                   <-- Database file (Generated after running migrations)
│
├── gateway_project/             <-- Core Configuration Folder
│   ├── __init__.py
│   ├── settings.py              <-- Project-wide settings
│   └── urls.py                  <-- Global routing links
│
└── smart_presence/              <-- App Folder
    ├── __init__.py
    ├── admin.py                 <-- Database UI registration
    ├── models.py                <-- Database schema (BeaconLog)
    └── management/
        └── commands/
            └── subscriber_daemon.py <-- The background MQTT storage script



## Installation & Setup
Follow these exact steps to set up the project on your machine from scratch.

1. Initialize Virtual Environment & Install Dependencies
Open your Command Prompt (cmd) inside the root folder (gateway_project/) and execute:
# Create an isolated environment named 'venv'
python -m venv venv

# Activate the virtual environment
venv\Scripts\activate

# Install Django and MQTT dependencies
pip install django paho-mqtt

2. Apply Database Migrations
Create your database tables based on the BeaconLog schema map:
python manage.py makemigrations
python manage.py migrate

3. Create an Administrator Account
To look inside the database via a clean web interface, create a superuser profile:
python manage.py createsuperuser

==============================================================================================================================

## Running the Project
To run this project fully, you will need two separate command prompt windows open at the same time (both with your venv active).

Window 1: Start the Background Ingestion Daemon
This process runs indefinitely, listening for new packets flowing from your Mosquitto broker and routing them to your database.
# Make sure your environment is active
venv\Scripts\activate

# Launch the custom ingestion command
python manage.py subscriber_daemon

Window 2: Start the Django Web Server
This allows you to access the database web UI and build your frontend application routes.
venv\Scripts\activate
python manage.py runserver

================================================================================================================================

## Verifying Stored Data (Admin UI Panel)
Once both windows are running and your ESP32-S3 starts pushing packets:

Open your web browser and navigate to: http://127.0.0.1:8000/admin/

Log in using your superuser credentials.

Click on Beacon logs under the Smart_Presence application tab.

You can see real-time updates of incoming items indexed by their MAC Address, RSSI values, and automatically extracted iBeacon UUID, Major, and Minor parameters.

===============================================================================================================================

## Troubleshooting Guide
Problem: The daemon screen stays blank or shows connection timeout flags.

Fix: Verify your Mosquitto Broker service is actively running on your Windows host machine using netstat -an | findstr 1883. Also ensure your ESP32-S3 is connected to your Windows Mobile Hotspot network.

Problem: Incoming logs show up in the terminal window but do not populate the admin panel.

Fix: Check that your virtual environment is properly activated and make sure you ran python manage.py migrate beforehand to establish the actual table layouts.

