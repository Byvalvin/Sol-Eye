from flask import Flask, request, jsonify, render_template
import pandas as pd
import numpy as np
import requests
from datetime import datetime
from flask_cors import CORS
from scipy.stats import f

app = Flask(__name__)
CORS(app)

NASA_API_URL = "https://power.larc.nasa.gov/api/temporal/hourly/point"
START_DATE = "20210101"
end_date = "20231231"

Potencia_panel = 590
TONC = 45
CCTPmax = -0.29
eficiencia_instalacion_fija = 0.7
eficiencia_inversor = 0.98
eficiencia_cables = 0.985

months, days, hours = [], [], []
input_rows = -1

def fetch_nasa_data(lat, lon):
    # end_date = datetime.now().strftime("%Y%m%d")
    params = {
        "start": START_DATE,
        "end": end_date,
        "latitude": lat,
        "longitude": lon,
        "community": "RE",
        "parameters": "ALLSKY_SFC_SW_DWN,ALLSKY_SFC_SW_DIFF,ALLSKY_SRF_ALB,T2M",
        "format": "CSV"
    }
    response = requests.get(NASA_API_URL, params=params)
    if response.status_code != 200:
        print(f"Error fetching NASA data: {response.status_code}")
        return None
    try:
        return process_nasa_data(response.text, lat)
    except Exception as e:
        print(f"Error processing NASA response: {e}")
        return None

def process_nasa_data(data, lat):
    from io import StringIO
    
    csv_data = StringIO(data) # Convert response text to a CSV-like stream
    lines = csv_data.readlines() # Read all lines first to check for metadata rows
    header_index = next(i for i, line in enumerate(lines) if "YEAR" in line) # Find the actual header line (NASA CSVs usually have metadata before)
    df = pd.read_csv(StringIO("\n".join(lines[header_index:])), sep=",") # Read CSV again, skipping metadata
    
    # Ensure necessary columns exist
    expected_columns = {"YEAR", "MO", "DY", "HR", "T2M", "ALLSKY_SFC_SW_DWN", "ALLSKY_SFC_SW_DIFF", "ALLSKY_SRF_ALB"}
    if not expected_columns.issubset(df.columns):
        raise ValueError(f"CSV missing required columns: {expected_columns - set(df.columns)}")

    # Compute additional values
    df["Irradiación Global Directa"] = df["ALLSKY_SFC_SW_DWN"] - df["ALLSKY_SFC_SW_DIFF"]
    
    diasJulianos = []
    for i in range(len(df)):
        if (i==0):
            diasJulianos.append(df['DY'][i]);
        elif (i<=len(data)):
            if(df['YEAR'][i] != df['YEAR'][i-1]):
                diasJulianos.append(1)
            else:
                if(df['DY'][i] != df['DY'][i-1]):
                    diasJulianos.append(diasJulianos[i-1] + 1)
                else:
                    diasJulianos.append(diasJulianos[i-1])
    
    # Rename columns for consistency
    df = df[['YEAR', 'MO', 'HR','Irradiación Global Directa','ALLSKY_SFC_SW_DIFF','ALLSKY_SRF_ALB','T2M']]
    df.rename(columns={
        "YEAR": "Año", "MO": "Mes", "HR": "Hora",
        "Irradiación Global Directa": "Radiación Directa",
        "ALLSKY_SFC_SW_DIFF": "Radiación Difusa", "ALLSKY_SRF_ALB": "Albedo", "T2M": "Temperatura"
    }, inplace=True)
    
    df.insert(2, 'Días Julianos', diasJulianos)
    df.rename(columns={
        'YEAR': 'Año', 'MO': 'Mes', 'HR': 'Hora',
        'Irradiación Global Directa': 'Radiación Directa',
        'ALLSKY_SFC_SW_DIFF': 'Radiación Difusa', 'ALLSKY_SRF_ALB': 'Albedo', 'T2M': 'Temperatura'
    }, inplace=True)

    Latitud = lat
    df['Ángulo Solar'] = 15 * df['Hora'] - 180
    df['Declinación'] = ((-1)**(Latitud<0))*23.45 * np.sin(np.radians((360/365 * (284 + df['Días Julianos']))))
    df['Zenith'] = np.arccos(np.sin(np.radians(Latitud)) * np.sin(np.radians(df['Declinación'])) + np.cos(np.radians(Latitud)) * np.cos(np.radians(df['Declinación'])) * np.cos(np.radians(df['Ángulo Solar'])))*180/np.pi
    #df['Zenith Aplicado'] = (df['Zenith']>90)*90 + (df['Zenith']<=90)*df['Zenith']
    df['Cos de Zenith'] = np.cos(np.radians(df['Zenith']))
    df['Altitud'] = 90 - df['Zenith']
    inclinacion = 3.7 + 0.69 * np.abs(Latitud)
    if Latitud >= 0:
        df['Cos theta'] = np.sin(np.radians(Latitud-inclinacion))*np.sin(np.radians(df['Declinación'])) + np.cos(np.radians(Latitud-inclinacion))*np.cos(np.radians(df['Declinación']))*np.cos(np.radians(df['Ángulo Solar']))
    else:
        df['Cos theta'] = np.sin(np.radians(Latitud+inclinacion))*np.sin(np.radians(df['Declinación'])) + np.cos(np.radians(Latitud+inclinacion))*np.cos(np.radians(df['Declinación']))*np.cos(np.radians(df['Ángulo Solar']))

    df['Horas Solares Pico'] = (df['Radiación Directa'] * df['Cos theta'] + df['Radiación Difusa']*0.5*(1 + np.cos(np.radians(inclinacion))) + df['Albedo']*0.5*(df['Radiación Directa'] + df['Radiación Difusa'])*(1 - np.cos(np.radians(inclinacion))))/ 1000
    factor_de_correcion = 1 #0.89104 --> Factor de correción
    df['Horas Solares'] = df['Horas Solares Pico'] * factor_de_correcion

    df["T_cel"] = df["Temperatura"] + df["Horas Solares"]*1000*(TONC-20)/800
    df["Eficiencia Esperada"] = (1 - CCTPmax * 0.01 * (25 - df["T_cel"])) * eficiencia_instalacion_fija * eficiencia_inversor * eficiencia_cables

    df_filtrado = df.loc[(df['Hora'] < 18) & (df['Hora'] > 7)]
    df_promedios = df_filtrado.groupby(['Mes', 'Días Julianos', 'Hora'])['Eficiencia Esperada'].mean().reset_index()
    # df_promedios = df_promedios[:-9] leap year

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

    global months, days, hours  # Ensure we modify the global lists
    global input_rows

    data = {
        "Month": months,
        "Day": days,
        "Hour": hours,
    }
    user_data = pd.DataFrame(data)
    month = user_data["Month"].iloc[0]
    day = user_data["Day"].iloc[0]
    hour = user_data["Hour"].iloc[0]
    specific_rows = df2.index[(df2['Mes'] == month) & (df2['Día'] == day) & (df2['Hora'] == hour)].tolist()

    df_filtered = df2.iloc[specific_rows[0] : specific_rows[0] + input_rows]
    if df_filtered.empty:
        print(input_rows, "epic fail error")
        return []
    df_filtered.insert(0, "X", list(range(input_rows))) # Ensure "X" is a sequential index like in the CSV function
    df_filtered = df_filtered[["X", "Eficiencia Esperada"]] # Select necessary columns

    return df_filtered.to_dict(orient="records")

@app.route('/get_solar_data', methods=['GET'])
def get_solar_data():
    lat = float(request.args.get('lat'))
    lon = float(request.args.get('lon'))
    solar_data = fetch_nasa_data(lat, lon)
    return jsonify({"solar_data": solar_data})


def process_uploaded_csv(file):
    global months, days, hours  # Ensure we modify the global lists
    global input_rows

    possible_delimiters = [',', '\t', ';', '|']
    for delimiter in possible_delimiters:
        try:
            df = pd.read_csv(file, delimiter=delimiter, skiprows=1, header=None)  # Skip header row
            if df.shape[1] == 4:  # Ensure exactly 4 columns
                break
        except Exception:
            continue
    else:
        return {"error": "Could not parse CSV file with expected 4 columns."}
    
    # if df.shape[0] < 24:
    #     return {"error": "CSV must have at least 24 rows of data."}

    # Extract Month, Day, and Hour as lists
    months = df.iloc[:, 0].tolist()
    days = df.iloc[:, 1].tolist()
    hours = df.iloc[:, 2].tolist()
    input_rows = df.shape[0]

    # Use 4th column as Measured Power
    measured_power_col = df.columns[3]
    df["Eficiencia Real"] = df[measured_power_col] / Potencia_panel

    df.insert(0, "X", list(range(input_rows))) # Set counter-based x-values for the graph
    df = df[["X", "Eficiencia Real"]] # Select necessary columns

    return df.to_dict(orient="records")


@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Empty file name"}), 400
    
    try:
        processed_data = process_uploaded_csv(file)
        if "error" in processed_data:
            return jsonify(processed_data), 400
        return jsonify({"csv_data": processed_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/compare_data', methods=['POST'])
def compare_data():
    data = request.get_json()
    solar_data = data.get("solar_data", [])
    csv_data = data.get("csv_data", [])
    
    if not solar_data or not csv_data:
        return jsonify({"error": "Both solar and CSV data are required"}), 400
    
    expected_efficiency = [entry["Eficiencia Esperada"] for entry in solar_data]
    actual_efficiency = [entry["Eficiencia Real"] for entry in csv_data]
    
    #test 1, the variance(F) test
    var_expected = np.var(expected_efficiency, ddof=1)
    var_actual = np.var(actual_efficiency, ddof=1)
    
    F_statistic = var_actual / var_expected if var_expected > 0 else float('inf')
    p_value = 1 - f.cdf(F_statistic, len(actual_efficiency) - 1, len(expected_efficiency) - 1)
    
    avg_efficiency = np.mean(actual_efficiency) / np.mean(expected_efficiency) * 100
    recommendation = "OK."
    
    if p_value < 0.05:
        recommendation = "Possible faulty wire."
    else:
        #test 2, the [5]% difference count test
        large_differences = sum(1 for exp, act in zip(expected_efficiency, actual_efficiency) if abs(exp - act) > 0.025)
        if large_differences > len(actual_efficiency) // 2:
            recommendation = "Possible dust or debris."
    
    return jsonify({
        "expected_power": round(np.mean(expected_efficiency) * 100, 2),
        "true_power": round(np.mean(actual_efficiency) * 100, 2),
        "efficiency": round(avg_efficiency, 2),
        "recommendation": recommendation
    })

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    # app.run(debug=True)
    app.run(debug=False)
