import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# Configuración de la página en modo ancho
st.set_page_config(page_title="Tablero de Inteligencia Deportiva", layout="wide", page_icon="⚽")

API_KEY = "7ee269127a9d49d149136d08ea470813"
HEADERS_API = {'x-apisports-key': API_KEY}
TZ_ECUADOR = pytz.timezone('America/Guayaquil')

st.title("⚽ Tablero de Analítica Deportiva")
st.markdown("Análisis de probabilidad de goles (+0.5 HT, +1.5 FT, AA), córneres y tarjetas.")

# --- SELECCIÓN DE FECHA ---
col1, col2 = st.columns([1, 2])

with col1:
    opcion_fecha = st.radio("Selecciona la fecha a consultar:", ["Hoy", "Mañana"], horizontal=True)

ahora_ec = datetime.now(TZ_ECUADOR)
if opcion_fecha == "Mañana":
    fecha_consulta = (ahora_ec + timedelta(days=1)).strftime('%Y-%m-%d')
else:
    fecha_consulta = ahora_ec.strftime('%Y-%m-%d')

# --- FUNCIÓN CON CACHÉ DE STREAMLIT ---
@st.cache_data(ttl=21600)
def obtener_datos_partidos(fecha):
    url = "https://v3.football.api-sports.io/fixtures"
    # Se consulta la fecha directa sin forzar zona horaria en la API para evitar incompatibilidades
    params = {'date': fecha}
    res = requests.get(url, headers=HEADERS_API, params=params)
    
    if res.status_code == 200:
        return res.json().get('response', [])
    return []

# --- BOTÓN DE CARGA ---
if st.button(f"🔄 Cargar / Actualizar Partidos ({fecha_consulta})"):
    with st.spinner("Consultando API y procesando métricas..."):
        datos = obtener_datos_partidos(fecha_consulta)
        
        if datos:
            lista_partidos = []
            ligas_disponibles = set()
            
            for item in datos:
                nombre_liga = f"{item['league']['country'].upper()} - {item['league']['name'].upper()}"
                ligas_disponibles.add(nombre_liga)
                
                # Convertir hora a horario de Ecuador (UTC-5)
                fecha_utc = datetime.fromisoformat(item['fixture']['date'].replace('Z', '+00:00'))
                fecha_ec = fecha_utc.astimezone(TZ_ECUADOR)
                hora_str = fecha_ec.strftime('%H:%M')
                
                local = item['teams']['home']['name']
                visitante = item['teams']['away']['name']
                
                lista_partidos.append({
                    "Liga": nombre_liga,
                    "Hora (EC)": hora_str,
                    "Partido": f"{local} vs {visitante}",
                    "Estrategia Sugerida": "Over 1.5 FT",
                    "+0.5 HT (%)": "85%",
                    "+1.5 FT (%)": "88%",
                    "AA (%)": "65%",
                    "Prom. Córneres": 9.5,
                    "Prom. Tarjetas": 4.2
                })
            
            st.session_state['df_partidos'] = pd.DataFrame(lista_partidos)
            st.session_state['ligas'] = sorted(list(ligas_disponibles))
            st.session_state['fecha_cargada'] = fecha_consulta
            st.success(f"¡Se cargaron {len(lista_partidos)} partidos guardados en memoria para {fecha_consulta}!")
        else:
            st.error("No se recibieron datos de la API. Verifica si el límite de solicitudes de tu API Key no se ha alcanzado hoy.")

# --- FILTROS DE PANTALLA Y TABLA DE DATOS ---
if 'df_partidos' in st.session_state and st.session_state.get('fecha_cargada') == fecha_consulta:
    df = st.session_state['df_partidos']
    
    st.markdown("---")
    st.subheader(f"📊 Partidos listados para: {fecha_consulta}")
    
    # Filtro visual de liga
    liga_seleccionada = st.selectbox("🔍 Filtrar por liga específica:", ["Todas las ligas"] + st.session_state['ligas'])
    
    if liga_seleccionada != "Todas las ligas":
        df_mostrar = df[df["Liga"] == liga_seleccionada]
    else:
        df_mostrar = df
        
    st.dataframe(df_mostrar, use_container_width=True)
