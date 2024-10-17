import paho.mqtt.client as mqtt
import joblib
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.impute import SimpleImputer
import json
import psycopg2
from psycopg2 import sql
import requests
import math
from datetime import datetime
import pytz
import struct
from collections import defaultdict
import pusher
import re

def clean_string(data):
    # Hanya izinkan huruf, angka, dan tanda -
    return re.sub(r'[^a-zA-Z0-9-]', '', data)  # Hanya izinkan huruf, angka, dan -


pusher_client = pusher.Pusher(
    app_id='1850421',
    key='65f308106c8272ff3922',
    secret='9d45275be93460720810',
    cluster='ap1',
    ssl=True
)

# Load the saved models and preprocessing objects
imputer = joblib.load('imputer.pkl')
scaler = joblib.load('scaler.pkl')
poly = joblib.load('poly.pkl')
knn_model_sys = joblib.load('knn_model_sys.pkl')
knn_model_dia = joblib.load('knn_model_dia.pkl')

# Define PostgreSQL settings
db_host = 'db'
db_name = 'mqtt_predictions'
db_user = 'james'
db_password = 'miguel'

# Define MQTT settings
broker ='202.157.186.97'
port = 1883
username = 'pablo'
password = 'costa'
topics = ['test/pub/ai/ALAT001','test/pub/ai/ALAT003']

# Store previous coordinates for distance calculation
previous_coordinates = {}
active_session_id = None
session_data = defaultdict(dict)

def haversine(lat1, lon1, lat2, lon2):
    """Calculate the great-circle distance between two points on the Earth."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    R = 6371.0  # Radius of Earth in kilometers
    return R * c

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
        for topic in topics:
            client.subscribe(topic)  # Subscribe to each topic
            print(f"Subscribed to topic: {topic}")
    else:
        print(f"Failed to connect, return code {rc}")
def get_age_from_db(session_name, serial_number):
    try:
        with psycopg2.connect(
                host=db_host,
                database=db_name,
                user=db_user,
                password=db_password
        ) as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT age 
                    FROM predictions.mst_sesi 
                    WHERE session_name = %s AND idalat_tx = %s 
                    LIMIT 1
                """
                cur.execute(query, (session_name, serial_number))
                result = cur.fetchone()
                if result is None:
                    print(f"No age found for session_name: {session_name} and serial_number: {serial_number}.")
                return result[0] if result else None
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return None


def on_message(client, userdata, msg):
    global active_session_id, session_data

    # Parse the received message
    data = msg.payload.decode()
    json_data = json.loads(data)
    session_id = json_data.get('session_id')
    serial_number = json_data.get('serial_number')
    age = get_age_from_db(session_id, serial_number)
    hr_2 = json_data.get('hr_2')
    spo2 = json_data.get('spo2')
    steps = json_data.get('steps')
    temp = json_data.get('temp')
    longitude = json_data.get('longitude')
    latitude = json_data.get('latitude')

    if age is None:
        print(f"Error: Age not found for session_id: {session_id} and serial_number: {serial_number}. Skipping VO2max calculation.")
        return  # Skip further processing if age is not found

    # Calculate VO2max
    vo2max = calculate_vo2max(age, steps, hr_2, spo2)

        # Publish received message to the test-ai topic
     
        
        # Publish to session-specific topic
        #client.publish(f"{session_id}/test", json.dumps(data))

        # Predict blood pressure
    bp_sys_pred, bp_dia_pred = predict_blood_pressure(hr_2, spo2, age)
        
        # Calculate stress index
    stress_index = stress_level(hr_2, spo2, bp_sys_pred, bp_dia_pred)

        # Calculate distance
    distance = calculate_distance(session_id, serial_number, latitude, longitude)
        
        # Retrieve IDAlatReceiver and user_id from mst_sesi based on session_id
    IDAlatReceiver, user_id = retrieve_session_info(session_id)

    if IDAlatReceiver is None or user_id is None:
       raise ValueError(f"No data found for session_id: {session_id}")

        # Prepare the payload for the API and MQTT output topic
    api_payload = {
            "IDAlatReceiver": IDAlatReceiver,
            "hr_2": hr_2,
            "latitude": latitude,
            "longitude": longitude,
            "predicted_dia": bp_dia_pred,
            "predicted_sys": bp_sys_pred,
            "serial_number": serial_number,
            "session_id": session_id,
            "spo2": spo2,
            "steps": steps,
            "stress_level": stress_index,
            "temp": temp,
            "user_id": user_id,
            "vo2max": vo2max,
            "tgljam": datetime.now().isoformat(),  # Current time in GMT+7
            "jarak": distance
        }

    session_data[session_id][serial_number] = api_payload
    combined_payload = session_data[session_id]
        
        # Trigger Pusher event
    pusher_client.trigger("read-sensor", session_id, json.dumps(combined_payload))
    print("Combined Payload:", json.dumps(combined_payload, indent=4))

        # Send data to the API
    send_data_to_api(api_payload)

        # Save data to PostgreSQL
    status_message = save_to_db(age, hr_2, spo2, bp_sys_pred, bp_dia_pred, stress_index, steps, longitude, latitude, temp, vo2max, serial_number, session_id, distance)
    print(status_message)

    if "Error" in status_message:
        client.publish("error/test", json.dumps({"error": status_message, "data": api_payload}))

def calculate_vo2max(age, steps, hr_2, spo2):
    """Calculate VO2max based on age, steps, heart rate, and oxygen saturation."""
    # Menghitung HR_max dan HR_rest
    hr_max = 220 - age
    hr_rest = hr_2  # Misalkan hr_2 adalah HR_rest

    if hr_rest == 0:
        return 0  # Meskipun ini sudah diperiksa sebelumnya

    # Hitung VO2max
    vo2max = 15 * (hr_max / hr_rest)
    return vo2max

def calculate_distance(session_id, serial_number, latitude, longitude):
    """Calculate distance from previous coordinates."""
    if (serial_number, session_id) in previous_coordinates:
        prev_lat, prev_lon = previous_coordinates[(serial_number, session_id)]
        distance = haversine(prev_lat, prev_lon, latitude, longitude)
    else:
        distance = 0

    # Update previous coordinates
    previous_coordinates[(serial_number, session_id)] = (latitude, longitude)
    return distance

def retrieve_session_info(session_id):
    """Retrieve IDAlatReceiver and user_id based on session_id."""
    with psycopg2.connect(
        host=db_host,
        database=db_name,
        user=db_user,
        password=db_password
    ) as conn:
        with conn.cursor() as cur:
            session_query = sql.SQL("""
                SELECT idalat_rx, iduser FROM predictions.mst_sesi WHERE session_name = %s
            """)
            cur.execute(session_query, (session_id,))
            return cur.fetchone()

def send_data_to_api(api_payload):
    """Send the API payload to the external API."""
    api_url = 'https://olahraga.oldmapps.com/api/save-sensor-data'
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(api_payload))
        response.raise_for_status()  # Raise an exception for HTTP errors
        print(f"Data sent to API, response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending data to API: {e}")
        # Publish error message to error/test topic
        mqtt_client.publish("error/test", json.dumps({"error": str(e), "data": api_payload}))

def predict_blood_pressure(hr_2, spo2, age):
    # Create a DataFrame for the input data
    input_data = pd.DataFrame({
        'age': [age],
        'hr_2': [hr_2],
        'spo2': [spo2]
    })
    
    # Impute missing values
    input_data_imputed = imputer.transform(input_data)
    
    # Add condition features based on reasonable defaults or assumptions
    input_data['hr_high_bp_high'] = (input_data['hr_2'] > 100).astype(int)
    input_data['hr_low_bp_low'] = (input_data['hr_2'] < 60).astype(int)
    input_data['spo2_low_bp_low'] = (input_data['spo2'] < 95).astype(int)
    input_data['spo2_low_hr_high'] = (input_data['spo2'] < 95).astype(int)

    # Combine features and condition features
    features_combined = np.hstack((input_data_imputed, input_data[['hr_high_bp_high', 'hr_low_bp_low', 'spo2_low_bp_low', 'spo2_low_hr_high']].values))
    
    # Scale features
    features_scaled = scaler.transform(features_combined)
    
    # Add polynomial features
    features_poly = poly.transform(features_scaled)
    
    # Predict systolic and diastolic blood pressure
    bp_sys_pred = knn_model_sys.predict(features_poly)
    bp_dia_pred = knn_model_dia.predict(features_poly)
    
    return bp_sys_pred[0], bp_dia_pred[0]

def stress_level(hr_2, spo2, bp_sys_pred, bp_dia_pred):
    """Calculate stress level based on heart rate, oxygen saturation, and blood pressure."""
    return hr_2 * 0.2 + spo2 * 0.1 + (bp_sys_pred + bp_dia_pred) * 0.7

def save_to_db(age, hr_2, spo2, bp_sys_pred, bp_dia_pred, stress_index, steps, longitude, latitude, temp, vo2max, serial_number, session_id, distance):
    try:
        bp_sys_pred = float(bp_sys_pred) if bp_sys_pred is not None else None
        bp_dia_pred = float(bp_dia_pred) if bp_dia_pred is not None else None
        stress_index = float(stress_index) if stress_index is not None else None
        temp = float(temp) if temp is not None else None
        vo2max = float(vo2max) if vo2max is not None else None
        longitude = str(longitude) if longitude is not None else None
        latitude = str(latitude) if latitude is not None else None
        steps = int(steps) if steps is not None else None
        with psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password
        ) as conn:
            with conn.cursor() as cur:
                # Query to get the `idsesi` based on the `session_name` (active_session_id)
                session_query = sql.SQL("""
                    SELECT idsesi FROM predictions.mst_sesi WHERE session_name = %s
                """)
                cur.execute(session_query, (session_id,))
                result = cur.fetchone()
                if result:
                    idsesi = result[0]
                else:
                    return f"Session ID {session_id} not found in the database."

                # Insert the data into the `mst_sensor` table
                insert_query = sql.SQL("""
                    INSERT INTO predictions.mst_sensor (
                         spo2, hr2, age, predicted_sys, predicted_dia, stress_level, steps, longitude, latitude, temp, vo2max, idalat_tx, idsesi, distance
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """)
                cur.execute(insert_query, (
                    spo2, hr_2, age, bp_sys_pred, bp_dia_pred, stress_index, steps, longitude,
                    latitude, temp, vo2max, serial_number, idsesi, distance
                ))
                
                # Commit the transaction
                conn.commit()
                return "Data saved successfully to the database."
                
    except Exception as e:
        return f"Error saving data to the database: {e}"
def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"Unexpected disconnection. Return code: {rc}")
    else:
        print("Disconnected successfully")

mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(username, password)

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

# Hubungkan ke broker dan mulai loop
mqtt_client.connect(broker, port, 60)
mqtt_client.loop_forever()
