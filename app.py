from flask import Flask, request, jsonify, render_template
import pandas as pd

app = Flask(__name__)

# Helper function to calculate true power from current and voltage
def calculate_true_power(df):
    true_power = None
    if 'power' in df.columns:
        # If the power column exists, use it directly
        true_power = df['power'].mean()  # Average power
    elif 'current' in df.columns and 'voltage' in df.columns:
        # If current and voltage columns exist, calculate power (P = V * I)
        df['power'] = df['current'] * df['voltage']
        true_power = df['power'].mean()  # Average power
    elif 'current' in df.columns:
        # If only current is given, assume a standard voltage
        standard_voltage = 12  # Example, can be adjusted based on the panel type
        df['power'] = df['current'] * standard_voltage
        true_power = df['power'].mean()  # Average power
    return true_power

# Endpoint to upload CSV and calculate power
@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    # Check if a file is part of the request
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    
    # Validate that the file is a CSV
    if not file.filename.endswith('.csv'):
        return jsonify({"error": "Only CSV files are allowed"}), 400

    try:
        # Read the CSV file using pandas
        df = pd.read_csv(file)
    except Exception as e:
        return jsonify({"error": f"Error reading the CSV file: {str(e)}"}), 400

    # Calculate true power
    true_power = calculate_true_power(df)
    
    if true_power is None:
        return jsonify({"error": "Required columns (current, voltage, or power) are missing in the CSV"}), 400

    return jsonify({
        "true_power": true_power
    })

# Endpoint to receive manual data input for current, voltage, and power
@app.route('/manual_data', methods=['POST'])
def manual_data():
    try:
        current = float(request.form['current'])
        voltage = float(request.form['voltage'])
        power = float(request.form['power'])
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid input. Ensure all values are numeric."}), 400

    # Calculate true power
    if current and voltage:
        true_power = current * voltage
    elif power:
        true_power = power
    else:
        return jsonify({"error": "Invalid data provided"}), 400

    return jsonify({
        "true_power": true_power
    })

# Route to calculate expected power based on location (using NASA data, for example)
@app.route('/get_expected_power', methods=['GET'])
def get_expected_power():
    try:
        lat = float(request.args.get('lat'))
        lon = float(request.args.get('lon'))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid latitude or longitude provided."}), 400
    
    # Example: You would fetch actual NASA data here based on lat/long
    # For simplicity, we are returning a mock expected power
    expected_power = 250  # Example expected power (W) from NASA data

    return jsonify({
        "expected_power": expected_power
    })

# Serve the frontend HTML file
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)



"""
pip install --cache-dir /local/scratch/Sol-Eye/Sol-Eye flask pandas
"""