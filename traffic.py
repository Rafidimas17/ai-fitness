from flask import Flask, request, jsonify
import psycopg2
import paho.mqtt.client as mqtt
import json
from  datetime import datetime
import pytz
import time  # Ensure this is included

app = Flask(__name__)


mqtt_client=None
broker = '202.157.186.97'
port = 1883
username = 'pablo'
password = 'costa'
mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(username, password)
mqtt_client.connect(broker, port)

def connect_mqtt():
    mqtt_client.connect(broker,port)
    mqtt_client.loop_start()
    
def get_db_connection():
    conn = psycopg2.connect(
        dbname="mqtt_predictions",
        user="james",
        password="miguel",
        host="db"
    )
    return conn
def subscribe_to_topic(topic):
    if mqtt_client and mqtt_client.is_connected():
        mqtt_client.subscribe(topic)
    else:
        print("MQTT client is not connected")
@app.route('/api/equipment/transmitters', methods=['GET'])
def get_transmitters():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # SQL query to get all receivers with their idAlat
    query = '''
        SELECT idAlat, name
        FROM predictions.mst_alat
        WHERE type = 'tx'
    '''
    cur.execute(query)
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    # Create a list of dictionaries with idAlat and name
    receivers = [{'idAlat': row[0], 'name': row[1]} for row in rows]
    
    return jsonify(receivers)

@app.route('/api/equipment/receivers', methods=['GET'])
def get_receivers():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # SQL query to get all receivers with their idAlat
    query = '''
        SELECT idAlat, name
        FROM predictions.mst_alat
        WHERE type = 'rx'
    '''
    cur.execute(query)
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    # Create a list of dictionaries with idAlat and name
    receivers = [{'idAlat': row[0], 'name': row[1]} for row in rows]
    
    return jsonify(receivers)

@app.route('/api/session', methods=['POST'])
def post_data_session():
    global mqtt_response
    mqtt_response = None

    try:
        # Read data from request JSON
        data = request.json
        
        # Extract data from the request
        mode = data.get('mode')
        session_id = data.get('session_id')
        idAlatTx_list = data.get('idAlatTx', [])
        idAlatRx = data.get('idAlatRx')
        idUser = data.get('idUser')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        ages = data.get('age', [])
        
        # Check for missing data
        if not all([session_id, idAlatRx, idUser, start_time, end_time]):
            return jsonify({'error': 'Missing data'}), 400

        if not isinstance(idAlatTx_list, list):
            return jsonify({'error': 'idAlatTx must be a list'}), 400

        if not isinstance(ages, list):
            return jsonify({'error': 'age must be a list'}), 400

        if len(ages) != len(idAlatTx_list):
            return jsonify({'error': 'The length of age must match the number of idAlatTx'}), 400
        
        # Connect to the database
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            # Check existence of idAlatRx
            cur.execute("SELECT COUNT(*) FROM predictions.mst_alat WHERE idalat = %s AND type = 'rx'", (idAlatRx,))
            rx_exists = cur.fetchone()[0] > 0
            
            if not rx_exists:
                raise ValueError(f'Receiver {idAlatRx} Tidak Tersedia')

            # Retrieve MAC address for idAlatRx
            cur.execute("SELECT mac_address FROM predictions.mst_alat WHERE idalat = %s", (idAlatRx,))
            rx_mac_address = cur.fetchone()
            if not rx_mac_address:
                raise ValueError(f'MAC address for Receiver {idAlatRx} not found')
            
            rx_mac_address = rx_mac_address[0]
            
            # Retrieve idmode
            cur.execute("SELECT idmode FROM predictions.mst_mode WHERE name = %s", (mode,))
            idmode = cur.fetchone()
            if not idmode:
                raise ValueError(f'Mode {mode} not found')
            
            idmode = idmode[0]
            
            # Retrieve MAC addresses for each idAlatTx
            mac_addresses = []
            for idAlatTx in idAlatTx_list:
                cur.execute("SELECT mac_address FROM predictions.mst_alat WHERE idalat = %s", (idAlatTx,))
                tx_mac_address = cur.fetchone()
                if tx_mac_address:
                    mac_addresses.append(tx_mac_address[0])
                else:
                    raise ValueError(f'MAC address for Transmitter {idAlatTx} not found')

            # Insert multiple records based on age list
            insert_query = """
            INSERT INTO predictions.mst_sesi (session_name, idalat_tx, idalat_rx, idmode, iduser, start_time, end_time, age)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            for idx, age in enumerate(ages):
                idAlatTx = idAlatTx_list[idx] if idx < len(idAlatTx_list) else idAlatTx_list[-1]
                cur.execute(insert_query, (session_id, idAlatTx, idAlatRx, idmode, idUser, start_time, end_time, age))
            
            conn.commit()
            
        except Exception as db_error:
            conn.rollback()  # Rollback the transaction in case of error
            raise db_error
        
        finally:
            # Ensure the database connection is closed
            cur.close()
            conn.close()

       
        # Success response
        return jsonify({'message': 'Session data inserted successfully'}), 201

    except Exception as e:
        # Handle exceptions and return an error response
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete', methods=['DELETE'])
def delete_session():
    try:
        # Ambil parameter query
        session_id = request.args.get('session_id')
        idalat = request.args.get('idalat')

        if not session_id:
            return jsonify({'error': 'session_id is required'}), 400

        conn = get_db_connection()
        cur = conn.cursor()

        # Cari sesi di mst_sesi berdasarkan session_name yang merupakan VARCHAR
        cur.execute("SELECT idalat_rx, idalat_tx FROM predictions.mst_sesi WHERE session_name = %s", (session_id,))
        session = cur.fetchone()

        if not session:
            return jsonify({'error': f'Session with id {session_id} not found'}), 404

        idalat_rx, idalat_tx = session

        # Ambil mac_address untuk idalat_rx
        cur.execute("SELECT mac_address FROM predictions.mst_alat WHERE idalat = %s", (idalat_rx,))
        rx_mac_address = cur.fetchone()

        if not rx_mac_address:
            return jsonify({'error': f'MAC address for Receiver with id {idalat_rx} not found'}), 404

        rx_mac_address = rx_mac_address[0]

        # Publish ke topik MQTT
        topic = f"connection/rejected/{rx_mac_address}"
        message = {"status": "stop"}

        # Periksa apakah idalat diberikan
        if idalat:
            # Ambil mac_address untuk idalat_tx
            cur.execute("SELECT mac_address FROM predictions.mst_alat WHERE idalat = %s", (idalat,))
            tx_mac_address = cur.fetchone()

            if not tx_mac_address:
                return jsonify({'error': f'MAC address for Transmitter with id {idalat} not found'}), 404

            tx_mac_address = tx_mac_address[0]
            message["mac_address"] = tx_mac_address

        def on_publish(client, userdata, mid):
            print(f"Message published with mid: {mid}")

        mqtt_client.on_publish = on_publish
        result = mqtt_client.publish(topic, json.dumps(message))
        
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            return jsonify({'error': 'Failed to publish message'}), 500

        # Hapus sesi dari mst_sesi berdasarkan session_name
        cur.execute("DELETE FROM predictions.mst_sesi WHERE session_name = %s", (session_id,))
        conn.commit()

        cur.close()
        conn.close()

        return jsonify({'message': 'Session deleted and message published'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0',port=4500)
