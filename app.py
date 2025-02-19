from flask import Flask, request, jsonify, render_template
import pandas as pd
import numpy as np
import requests
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

NASA_API_URL = "https://power.larc.nasa.gov/api/temporal/hourly/point"
START_DATE = "20210101"

def fetch_nasa_data(lat, lon):
    end_date = datetime.now().strftime("%Y%m%d")
    params = {
        "start": START_DATE,
        "end": end_date,
        "latitude": lat,
        "longitude": lon,
        "community": "RE",
        "parameters": "ALLSKY_SFC_SW_DWN,ALLSKY_SFC_SW_DIFF,ALLSKY_SFC_SW_DNI,T2M,CLRSKY_SFC_SW_DWN",
        "format": "JSON"
    }
    response = requests.get(NASA_API_URL, params=params)
    if response.status_code != 200:
        return None
    data = response.json()
    return process_nasa_data(data, lat)

def process_nasa_data(data, lat):
    df = pd.DataFrame()
    df["YEAR"] = [int(y[:4]) for y in data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"].keys()]
    df["MO"] = [int(y[4:6]) for y in data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"].keys()]
    df["DY"] = [int(y[6:8]) for y in data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"].keys()]
    df["HR"] = [int(y[8:]) for y in data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"].keys()]
    
    df["ALLSKY_SFC_SW_DWN"] = list(data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"].values())
    df["ALLSKY_SFC_SW_DIFF"] = list(data["properties"]["parameter"]["ALLSKY_SFC_SW_DIFF"].values())
    df["ALLSKY_SFC_SW_DNI"] = list(data["properties"]["parameter"]["ALLSKY_SFC_SW_DNI"].values())
    df["T2M"] = list(data["properties"]["parameter"]["T2M"].values())
    df["CLRSKY_SFC_SW_DWN"] = list(data["properties"]["parameter"]["CLRSKY_SFC_SW_DWN"].values())
    
    df["Irradiación Global Directa"] = df["ALLSKY_SFC_SW_DWN"] - df["ALLSKY_SFC_SW_DIFF"]
    
    diasJulianos = []
    for i in range(len(df)):
        if i == 0:
            diasJulianos.append(df['DY'][i])
        elif df['YEAR'][i] != df['YEAR'][i-1]:
            diasJulianos.append(1)
        elif df['DY'][i] != df['DY'][i-1]:
            diasJulianos.append(diasJulianos[i-1] + 1)
        else:
            diasJulianos.append(diasJulianos[i-1])
    
    df.insert(2, 'Días Julianos', diasJulianos)
    df["Ángulo Solar"] = 15 * df["HR"] - 180
    df["Declinación"] = ((-1)**(lat < 0)) * 23.45 * np.sin(np.radians((360/365 * (284 + df["Días Julianos"]))))
    df["Zenith"] = np.arccos(np.sin(np.radians(lat)) * np.sin(np.radians(df["Declinación"])) + np.cos(np.radians(lat)) * np.cos(np.radians(df["Declinación"])) * np.cos(np.radians(df["Ángulo Solar"]))) * 180 / np.pi
    df["Zenith Aplicado"] = np.where(df["Zenith"] > 90, 90, df["Zenith"])
    df["Cos de Zenith"] = np.cos(np.radians(df["Zenith Aplicado"]))
    df["Altitud"] = 90 - df["Zenith Aplicado"]
    df["Azimuth al Norte"] = np.arcsin(np.cos(np.radians(df["Declinación"])) * np.sin(np.radians(df["Ángulo Solar"])) / np.cos(np.radians(df["Altitud"]))) * 180 / np.pi
    df["Prueba"] = ((np.cos(np.radians(df["Ángulo Solar"])) < np.tan(np.radians(df["Declinación"])) / np.tan(np.radians(lat))) & (lat < 0)) + ((np.cos(np.radians(df["Ángulo Solar"])) > np.tan(np.radians(df["Declinación"])) / np.tan(np.radians(lat))) & (lat >= 0))
    df["Azimuth al Sur"] = np.where(df["Prueba"], df["Azimuth al Norte"], np.where(df["HR"] < 12, -180 + abs(df["Azimuth al Norte"]), 180 + df["Azimuth al Norte"]))
    
    azimuth_del_panel_eo = np.where(df["Azimuth al Sur"] < 0, -90, np.where(df["Azimuth al Sur"] == 0, 0, 90))
    tangente_angulo_inclinacion_eo = np.tan(np.radians(df["Zenith"])) * abs(np.cos(np.radians(azimuth_del_panel_eo - df["Azimuth al Sur"])))
    angulo_ideal_eo = np.where(df["Zenith"] >= 90, 90, np.arctan(tangente_angulo_inclinacion_eo) * 180 / np.pi)
    angulo_inclinacion_eo = np.where(angulo_ideal_eo > 60, 60, angulo_ideal_eo)
    df["Factor K"] = angulo_inclinacion_eo  # Placeholder if needed
    df["Horas Solares"] = (df["Factor K"] * df["Irradiación Global Directa"]) / 1000 * 0.89104
    
    df = df[(df["HR"] >= 8) & (df["HR"] <= 17)]
    return df.tail(25).to_dict(orient="records")

@app.route('/get_solar_data', methods=['GET'])
def get_solar_data():
    try:
        lat = float(request.args.get('lat'))
        lon = float(request.args.get('lon'))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid latitude or longitude provided."}), 400
    
    solar_data = fetch_nasa_data(lat, lon)
    if solar_data is None:
        return jsonify({"error": "Failed to fetch data from NASA API."}), 500
    
    return jsonify({"solar_data": solar_data})

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)




"""
pip install --cache-dir /local/scratch/Sol-Eye/Sol-Eye flask flask-cors pandas
"""
