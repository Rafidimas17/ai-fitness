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

# Load the saved models and preprocessing objects
imputer = joblib.load('imputer.pkl')
scaler = joblib.load('scaler.pkl')
poly = joblib.load('poly.pkl')
knn_model_sys = joblib.load('knn_model_sys.pkl')
knn_model_dia = joblib.load('knn_model_dia.pkl')


serial_number='ALT-001'
# Define MQTT settings
broker = '202.157.186.97'
port = 1883
username = 'pablo'
password = 'costa'
input_topic = f'{serial_number}/pub/ai' 
output_topic = f'{serial_number}/completed/ai' 

# topic = read-sensor/{session_id}

# Define PostgreSQL settings
db_host = 'db'
db_name = 'mqtt_predictions'
db_user = 'james'
db_password = 'miguel'

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected successfully")
        client.subscribe(input_topic)
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    # Parse the received message
    data = json.loads(msg.payload)
    hr_2 = data['hr_2']
    spo2 = data['spo2']
    age = data['age']
    steps = data['steps']
    longitude = data['longitude']
    latitude = data['latitude']
    temp = data['temp']
    vo2max = data['vo2max']
    user_id=data['user_id']
    session_id=data['session_id']
    serial_number=data['serial_number'] 
       
    
    # Predict blood pressure
    bp_sys_pred, bp_dia_pred = predict_blood_pressure(hr_2, spo2, age)
    
    # Calculate stress index
    stress_index = stress_level(hr_2, spo2, bp_sys_pred, bp_dia_pred)
    
    # Prepare predictions
    predictions = {
        'predicted_sys': bp_sys_pred,
        'predicted_dia': bp_dia_pred,
        'hr_2': hr_2,
        'spo2': spo2,
        'vo2max': vo2max,
        'temp': temp,
        'steps': steps,
        'longitude': longitude,
        'latitude': latitude,
        'stress_level': stress_index,
        'user_id':user_id,
        'session_id':session_id,
        'serial_number':serial_number 
    }
    
    # Publish predictions
    client.publish(output_topic, json.dumps(predictions))
    
    api_url = 'http://web_iot_system:80/api/save-sensor-data'
    headers = {'Content-Type': 'application/json','Accept': 'application/json'}
    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(predictions))
        response.raise_for_status()  # Raise an exception for HTTP errors
        print(f"Data sent to API, response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending data to API: {e}")

    # Save data to PostgreSQL (optional)
    status_message = save_to_db(age, hr_2, spo2, bp_sys_pred, bp_dia_pred, stress_index, steps, longitude, latitude, temp, vo2max)
    print(status_message)

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

def stress_level(hr, spo2, tekanan_darah_sistolik, tekanan_darah_diastolik):
    # Bobot parameter (dapat disesuaikan sesuai kebutuhan)
    bobot_hr = 0.5
    bobot_spo2 = 0.3
    bobot_tekanan_darah = 0.2
    
    # Menghitung indeks stres
    indeks_stres = (bobot_hr * hr) + (bobot_spo2 * (120 - spo2)) + (bobot_tekanan_darah * tekanan_darah_sistolik)
    
    return indeks_stres

def save_to_db(age, hr_2, spo2, bp_sys_pred, bp_dia_pred, stress_level, steps, longitude, latitude, temp, vo2max):
    try:
        # Convert NumPy float64 to Python float
        bp_sys_pred = float(bp_sys_pred)
        bp_dia_pred = float(bp_dia_pred)
        stress_level = float(stress_level)
        temp = float(temp)
        vo2max = float(vo2max)
        longitude = str(longitude)
        latitude = str(latitude)

        # Convert steps to integer
        steps = int(steps)

        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password
        )
        cur = conn.cursor()

        # Insert query
        insert_query = sql.SQL("""
            INSERT INTO predictions.predictions (age, hr_2, spo2, predicted_sys, predicted_dia, stress_level, steps, longitude, latitude, temp, vo2max)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """)
        
        # Execute the query
        cur.execute(insert_query, (age, hr_2, spo2, bp_sys_pred, bp_dia_pred, stress_level, steps, longitude, latitude, temp, vo2max))

        # Commit the transaction
        conn.commit()

        # Close the cursor and connection
        cur.close()
        conn.close()
        
        return {
            'status': 'success',
            'message': 'Data saved to database successfully'
        }
    except Exception as e:
        print(f"Error saving data to database: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }

# Create an MQTT client instance
client = mqtt.Client()
client.username_pw_set(username, password)
client.on_connect = on_connect
client.on_message = on_message

# Connect to the MQTT broker
client.connect(broker, port, 60)

# Start the loop
client.loop_forever()
