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
    
    # SQL query to get all transmitters
    query = '''
        SELECT name
        FROM predictions.mst_alat
        WHERE tipe = 'tx'
    '''
    cur.execute(query)
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    names = [row[0] for row in rows]
    return jsonify(names)

@app.route('/api/equipment/receivers', methods=['GET'])
def get_receivers():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # SQL query to get all receivers
    query = '''
        SELECT name
        FROM predictions.mst_alat
        WHERE tipe = 'rx'
    '''
    cur.execute(query)
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    names = [row[0] for row in rows]
    return jsonify(names)

@app.route('/api/session', methods=['POST'])
def post_data_session():
    try:
        # Read data from request JSON
        data = request.json
        
        # Extract data from the request
        idAlatTx_list = data.get('idAlatTx', [])
        idAlatRx = data.get('idAlatRx')
        idUser = data.get('idUser')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        # Check for missing data
        if not all([idAlatRx, idUser, start_time, end_time]):
            return jsonify({'error': 'Missing data'}), 400

        if not isinstance(idAlatTx_list, list):
            return jsonify({'error': 'idAlatTx must be a list'}), 400
        
        # Connect to the database
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check existence of idAlatRx
        cur.execute("SELECT COUNT(*) FROM predictions.mst_alat WHERE idAlat = %s AND tipe = 'rx'", (idAlatRx,))
        rx_exists = cur.fetchone()[0] > 0
        
        if not rx_exists:
            cur.close()
            conn.close()
            return jsonify({'error': f'Receiver {idAlatRx} Tidak Tersedia'}), 404
        
        # Process each idAlatTx
        for idAlatTx in idAlatTx_list:
            # Check existence of idAlatTx
            cur.execute("SELECT COUNT(*) FROM predictions.mst_alat WHERE idAlat = %s AND tipe = 'tx'", (idAlatTx,))
            tx_exists = cur.fetchone()[0] > 0
            
            if not tx_exists:
                cur.close()
                conn.close()
                return jsonify({'error': f'Transmitter {idAlatTx} Tidak Tersedia'}), 404
            
            # SQL to insert data
            insert_query = """
            INSERT INTO predictions.mst_sesi (idAlatTx, idAlatRx, idUser, start_time, end_time)
            VALUES (%s, %s, %s, %s, %s)
            """
            
            # Insert data
            cur.execute(insert_query, (idAlatTx, idAlatRx, idUser, start_time, end_time))
            conn.commit()
        
        # Close connection and cursor
        cur.close()
        conn.close()
        
        # Success response
        return jsonify({'message': 'Session data inserted successfully'}), 201
    
    except Exception as e:
        # Handle errors
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=4500)
