from flask import Flask, request, jsonify
import psycopg2

app = Flask(__name__)

def get_db_connection():
    conn = psycopg2.connect(
        dbname="mqtt_predictions",
        user="james",
        password="miguel",
        host="db"
    )
    return conn

@app.route('/api/equipment/transmitters', methods=['GET'])
def get_transmitters():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # SQL query to get all receivers with their idAlat
    query = '''
        SELECT idAlat, name
        FROM predictions.mst_alat
        WHERE tipe = 'tx'
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
        WHERE tipe = 'rx'
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
    try:
        # Read data from request JSON
        data = request.json
        
        # Extract data from the request
        session_id = data.get('session_id')
        idAlatTx_list = data.get('idAlatTx', [])
        idAlatRx = data.get('idAlatRx')
        idUser = data.get('idUser')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        # Check for missing data
        if not all([session_id, idAlatRx, idUser, start_time, end_time]):
            return jsonify({'error': 'Missing data'}), 400

        if not isinstance(idAlatTx_list, list):
            return jsonify({'error': 'idAlatTx must be a list'}), 400
        
        # Connect to the database
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check existence of idAlatRx
        cur.execute("SELECT COUNT(*) FROM predictions.mst_alat WHERE name = %s AND tipe = 'rx'", (idAlatRx,))
        rx_exists = cur.fetchone()[0] > 0
        
        if not rx_exists:
            cur.close()
            conn.close()
            return jsonify({'error': f'Receiver {idAlatRx} Tidak Tersedia'}), 404
        
        # Retrieve MAC address for idAlatRx
        cur.execute("SELECT mac_address FROM predictions.mst_alat WHERE name = %s", (idAlatRx,))
        rx_mac_address = cur.fetchone()
        if not rx_mac_address:
            cur.close()
            conn.close()
            return jsonify({'error': f'MAC address for Receiver {idAlatRx} not found'}), 404
        
        rx_mac_address = rx_mac_address[0]

        # Retrieve MAC addresses for each idAlatTx
        mac_addresses = []
        for idAlatTx in idAlatTx_list:
            cur.execute("SELECT mac_address FROM predictions.mst_alat WHERE name = %s", (idAlatTx,))
            tx_mac_address = cur.fetchone()
            if tx_mac_address:
                mac_addresses.append(tx_mac_address[0])
            else:
                cur.close()
                conn.close()
                return jsonify({'error': f'MAC address for Transmitter {idAlatTx} not found'}), 404

        # SQL to insert data
        insert_query = """
        INSERT INTO predictions.mst_sesi (session_name, idAlatTx, idAlatRx, idUser, start_time, end_time)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        # Insert data
        cur.execute(insert_query, (session_id, idAlatTx_list[0], idAlatRx, idUser, start_time, end_time))
        conn.commit()
        
        # Publish MQTT message with MAC addresses for idAlatTx
        mqtt_topic = f'connection/init/{rx_mac_address}'
        mqtt_message = {'mac_addresses': mac_addresses}
        
        # Ensure the MQTT client is connected
        if not mqtt_client.is_connected():
            connect_mqtt()
        
        # Publish the message
        mqtt_client.publish(mqtt_topic, json.dumps(mqtt_message))
        
        # Close connection and cursor
        cur.close()
        conn.close()
        
        # Success response
        return jsonify({'message': 'Session data inserted successfully'}), 201
    
    except Exception as e:
        # Handle errors
        return jsonify({'error': str(e)}), 500
except Exception as e:
        # Handle errors
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=4500)
