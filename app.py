from flask import Flask, request, jsonify, render_template
import pandas as pd
import numpy as np
import requests
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

NASA_API_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
START_DATE = "20180101"

def fetch_nasa_data(lat, lon):
    # end_date = datetime.now().strftime("%Y%m%d")
    end_date = "20231231"
    params = {
        "start": START_DATE,
        "end": end_date,
        "latitude": lat,
        "longitude": lon,
        "community": "RE",
        "parameters": "ALLSKY_SFC_SW_DWN,ALLSKY_SFC_SW_DIFF,ALLSKY_SRF_ALB,T2M",
        "format": "JSON"
    }
    response = requests.get(NASA_API_URL, params=params)
    if response.status_code != 200:
        print(f"Error fetching NASA data: {response.status_code}")
        return None
    try:
        return process_nasa_data(response.json(), lat)
    except Exception as e:
        print(f"Error processing NASA response: {e}")
        return None

def process_nasa_data(data, lat):
    df = pd.DataFrame({
        "YEAR": [int(y[:4]) for y in data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"].keys()],
        "MO": [int(y[4:6]) for y in data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"].keys()],
        "DY": [int(y[6:8]) for y in data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"].keys()],
        "HR": list(range(len(data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]))),
        "T2M": list(data["properties"]["parameter"]["T2M"].values()),
        "ALLSKY_SFC_SW_DWN": list(data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"].values()),
        "ALLSKY_SFC_SW_DIFF": list(data["properties"]["parameter"]["ALLSKY_SFC_SW_DIFF"].values()),
        "ALLSKY_SRF_ALB": list(data["properties"]["parameter"]["ALLSKY_SRF_ALB"].values()),
    })
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
    df.rename(columns={
        'YEAR': 'Año', 'MO': 'Mes', 'HR': 'Hora',
        'Irradiación Global Directa': 'Radiación Directa',
        'ALLSKY_SFC_SW_DIFF': 'Radiación Difusa', 'ALLSKY_SRF_ALB': 'Albedo', 'T2M': 'Temperatura'
    }, inplace=True)
    
    df["Ángulo Solar"] = 15 * df["Hora"] - 180
    df["Declinación"] = ((-1)**(lat < 0)) * 23.45 * np.sin(np.radians((360/365 * (284 + df["Días Julianos"]))))
    df["Zenith"] = np.arccos(np.sin(np.radians(lat)) * np.sin(np.radians(df["Declinación"])) +
                              np.cos(np.radians(lat)) * np.cos(np.radians(df["Declinación"])) *
                              np.cos(np.radians(df["Ángulo Solar"]))) * 180 / np.pi
    df["Cos de Zenith"] = np.cos(np.radians(df["Zenith"]))
    df["Altitud"] = 90 - df["Zenith"]
    inclinacion = 3.7 + 0.69 * abs(lat)
    df["Cos theta"] = (np.sin(np.radians(lat - inclinacion)) * np.sin(np.radians(df["Declinación"])) +
                         np.cos(np.radians(lat - inclinacion)) * np.cos(np.radians(df["Declinación"])) *
                         np.cos(np.radians(df["Ángulo Solar"])))
    df["Horas Solares Pico"] = (
        (df["Radiación Directa"] * df["Cos theta"] +
         df["Radiación Difusa"] * 0.5 * (1 + np.cos(np.radians(inclinacion))) +
         df["Albedo"] * 0.5 * (df["Radiación Directa"] + df["Radiación Difusa"]) *
         (1 - np.cos(np.radians(inclinacion)))) / 1000)
    
    factor_de_correcion = 1
    df["Horas Solares"] = df["Horas Solares Pico"] * factor_de_correcion
    
    Potencia_panel = 590
    TONC = 45
    CCTPmax = -0.29
    eficiencia_instalacion_fija = 0.7
    eficiencia_inversor = 0.98
    eficiencia_cables = 0.985
    
    df["T_cel"] = df["Temperatura"] + df["Horas Solares"] * 1000 * (TONC - 20) / 800
    df["Eficiencia Esperada"] = ((1 - CCTPmax * 0.01 * (25 - df["T_cel"])) *
                                  eficiencia_instalacion_fija * eficiencia_inversor * eficiencia_cables)
    df_filtrado = df[(df["Hora"] > 7) & (df["Hora"] < 17)]
    df_promedios = df_filtrado.groupby(["Mes", "Días Julianos", "Hora"])["Eficiencia Esperada"].mean().reset_index()

    # Crear tabla de referencia de días julianos
    dias_por_mes = {
        1: 31,  2: 28,  3: 31,  4: 30,  5: 31,  6: 30,
        7: 31,  8: 31,  9: 30, 10: 31, 11: 30, 12: 31
    }

    # Calcular días julianos acumulados
    dias_acumulados = {mes: sum(list(dias_por_mes.values())[:mes-1]) for mes in dias_por_mes}

    # Función para convertir días julianos en día del mes
    def convertir_dia_juliano(dia_juliano):
        for mes, acumulado in dias_acumulados.items():
            if dia_juliano <= acumulado + dias_por_mes[mes]:
                dia_del_mes = dia_juliano - acumulado
                return mes, dia_del_mes
        return None, None  # Por si hay un error


    df2 = df_promedios

    df2[['Mes', 'Día']] = df_promedios['Días Julianos'].apply(lambda x: pd.Series(convertir_dia_juliano(x)))

    df2 = df_promedios.drop(columns=['Días Julianos'])

    columna = df2.pop('Día')
    df2.insert(1, 'Día', columna)
    df2 = df2.tail(25)
    return df2.to_dict(orient="records")

@app.route('/get_solar_data', methods=['GET'])
def get_solar_data():
    lat = float(request.args.get('lat'))
    lon = float(request.args.get('lon'))
    solar_data = fetch_nasa_data(lat, lon)
    return jsonify({"solar_data": solar_data})

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)
