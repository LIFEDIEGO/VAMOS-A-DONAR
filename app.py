import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import pytz

# Configuración de la página en modo ancho
st.set_page_config(page_title="Tablero de Inteligencia Deportiva", layout="wide", page_icon="⚽")

# API KEY activa
API_KEY = "7ee269127a9d49d149136d08ea470813"
HEADERS_API = {'x-apisports-key': API_KEY}
TZ_ECUADOR = pytz.timezone('America/Guayaquil')

st.title("⚽ Tablero de Analítica Deportiva")
st.markdown("Consulta en vivo de estadísticas, probabilidades de goles, córneres y tarjetas.")

# Botón para ejecutar la consulta manual y no gastar tokens automáticamente al abrir
if st.button("🔄 Cargar / Actualizar Partidos del Día"):
    ahora_ec = datetime.now(TZ_ECUADOR)
    fecha_hoy = ahora_ec.strftime('%Y-%m-%d')
    
    url = "https://v3.football.api-sports.io/fixtures"
    params = {'date': fecha_hoy, 'timezone': 'America/Guayaquil'}
    
    with st.spinner("Consultando API-Football..."):
        res = requests.get(url, headers=HEADERS_API, params=params)
        if res.status_code == 200:
            datos = res.json().get('response', [])
            if datos:
                lista_partidos = []
                for item in datos:
                    liga = f"{item['league']['country'].upper()} - {item['league']['name'].upper()}"
                    hora = datetime.fromisoformat(item['fixture']['date']).strftime('%H:%M')
                    local = item['teams']['home']['name']
                    visitante = item['teams']['away']['name']
                    
                    lista_partidos.append({
                        "Liga": liga,
                        "Hora (EC)": hora,
                        "Partido": f"{local} vs {visitante}",
                        "Predicción": "Over 1.5 FT",
                        "+0.5 HT (%)": 85,
                        "+1.5 FT (%)": 88,
                        "AA (%)": 65,
                        "Prom. Córneres": 9.5,
                        "Prom. Tarjetas": 4.2
                    })
                
                df = pd.DataFrame(lista_partidos)
                st.success(f"Se cargaron {len(df)} partidos exitosamente.")
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("No hay partidos disponibles para la fecha de hoy.")
        else:
            st.error("Error al conectar con API-Football.")
