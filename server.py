from flask import Flask, request, jsonify
import datetime
import os
import csv

app = Flask(__name__)
LOG_FILE = 'tracking_log.csv'
CSV_HEADER = ['timestamp', 'dist0', 'dist1', 'dist2', 'dist3', 'x', 'y']

def ensure_header():
    """Create file with header if it doesn't exist or is empty."""
    if not os.path.exists(LOG_FILE) or os.path.getsize(LOG_FILE) == 0:
        with open(LOG_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)

@app.route('/log', methods=['POST'])
def log_data():
    ensure_header()
    data = request.get_json(silent=True) or {}

    # Validate required fields (now includes dist3)
    required = ['dist0', 'dist1', 'dist2', 'dist3', 'x', 'y']
    missing = [k for k in required if k not in data]
    if missing:
        return jsonify({'status': 'error', 'missing': missing}), 400

    try:
        # Coerce to float for safety
        row = [
            datetime.datetime.now().isoformat(),
            float(data['dist0']),
            float(data['dist1']),
            float(data['dist2']),
            float(data['dist3']),
            float(data['x']),
            float(data['y']),
        ]
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'invalid numeric payload'}), 400

    with open(LOG_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(row)

    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    # Host 0.0.0.0 on port 5050 to match the tag’s SERVER_URL
    app.run(host='0.0.0.0', port=5050)
