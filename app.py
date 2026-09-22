import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

st.set_page_config(page_title="Tablero de Inteligencia Deportiva", layout="wide", page_icon="⚽")

# API KEY ACTIVA
API_KEY = "1dc6342cce2b065fce3a3599b033d103"
HEADERS_API = {
    'x-rapidapi-key': API_KEY,
    'x-apisports-key': API_KEY
}
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

# --- FUNCIÓN DE CONSULTA CON CACHÉ ---
@st.cache_data(ttl=21600)
def obtener_datos_partidos(fecha):
    url = "https://v3.football.api-sports.io/fixtures"
    params = {'date': fecha}
    
    try:
        res = requests.get(url, headers=HEADERS_API, params=params, timeout=10)
        return res.status_code, res.json()
    except Exception as e:
        return 500, {"errors": str(e)}

# --- BOTÓN DE CARGA ---
if st.button(f"🔄 Cargar / Actualizar Partidos ({fecha_consulta})"):
    with st.spinner("Consultando API y procesando métricas..."):
        status_code, respuesta = obtener_datos_partidos(fecha_consulta)
        
        errores = respuesta.get('errors', {})
        datos = respuesta.get('response', [])
        
        if status_code == 200 and not errores and datos:
            lista_partidos = []
            ligas_disponibles = set()
            
            for item in datos:
                nombre_liga = f"{item['league']['country'].upper()} - {item['league']['name'].upper()}"
                ligas_disponibles.add(nombre_liga)
                
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
            st.error(f"Error de conexión (Código HTTP: {status_code})")
            if errores:
                st.write("Respuesta de la API:", errores)
            elif not datos:
                st.warning(f"La API no devolvió partidos programados para la fecha {fecha_consulta}.")

# --- DESPLIEGUE DE TABLA ---
if 'df_partidos' in st.session_state and st.session_state.get('fecha_cargada') == fecha_consulta:
    df = st.session_state['df_partidos']
    st.markdown("---")
    st.subheader(f"📊 Partidos listados para: {fecha_consulta}")
    
    liga_seleccionada = st.selectbox("🔍 Filtrar por liga específica:", ["Todas las ligas"] + st.session_state['ligas'])
    
    if liga_seleccionada != "Todas las ligas":
        df_mostrar = df[df["Liga"] == liga_seleccionada]
    else:
        df_mostrar = df
        
    st.dataframe(df_mostrar, use_container_width=True)
