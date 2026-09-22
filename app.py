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
st.markdown("Análisis de probabilidad de goles (+0.5 HT, +1.5 FT, AA), córneres y tarjetas por ligas desplegables.")

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
        res = requests.get(url, headers=HEADERS_API, params=params, timeout=12)
        return res.status_code, res.json()
    except Exception as e:
        return 500, {"errors": str(e)}

# --- BOTÓN DE CARGA ---
if st.button(f"🔄 Cargar / Actualizar Partidos ({fecha_consulta})"):
    with st.spinner("Procesando partidos y organizando ligas..."):
        status_code, respuesta = obtener_datos_partidos(fecha_consulta)
        
        errores = respuesta.get('errors', {})
        datos = respuesta.get('response', [])
        
        if status_code == 200 and not errores and datos:
            lista_partidos = []
            
            for item in datos:
                nombre_liga = f"{item['league']['country'].upper()} - {item['league']['name'].upper()}"
                
                fecha_utc = datetime.fromisoformat(item['fixture']['date'].replace('Z', '+00:00'))
                fecha_ec = fecha_utc.astimezone(TZ_ECUADOR)
                hora_str = fecha_ec.strftime('%H:%M')
                
                local = item['teams']['home']['name']
                visitante = item['teams']['away']['name']
                
                # Valores estándar fijados para prueba de interfaz
                lista_partidos.append({
                    "Liga": nombre_liga,
                    "Hora (EC)": hora_str,
                    "Partido": f"{local} vs {visitante}",
                    "Local": local,
                    "Visitante": visitante,
                    "Estrategia Sugerida": "Over 1.5 FT",
                    "+0.5 HT (%)": 85,
                    "+1.5 FT (%)": 88,
                    "AA (%)": 65,
                    "Prom. Córneres": 9.5,
                    "Prom. Tarjetas": 4.2
                })
            
            st.session_state['df_partidos'] = pd.DataFrame(lista_partidos)
            st.session_state['fecha_cargada'] = fecha_consulta
            st.success(f"¡Se organizaron {len(lista_partidos)} partidos por ligas para {fecha_consulta}!")
            
        else:
            st.error(f"Error de conexión (Código HTTP: {status_code})")
            if errores:
                st.write("Respuesta de la API:", errores)

# --- PANEL DE FILTROS Y DESPLIEGUE DESPLEGABLE ---
if 'df_partidos' in st.session_state and st.session_state.get('fecha_cargada') == fecha_consulta:
    df = st.session_state['df_partidos'].copy()
    
    st.markdown("---")
    st.subheader(f"📊 Partidos listados para: {fecha_consulta}")
    
    # --- FILTROS DE BÚSQUEDA Y PORCENTAJES ---
    f_col1, f_col2, f_col3 = st.columns([2, 1.5, 1.5])
    
    with f_col1:
        busqueda_equipo = st.text_input("🔍 Buscar por nombre de equipo:", placeholder="Ej. Toluca, Barcelona, Lazio...")
    
    with f_col2:
        filtro_probabilidad = st.selectbox(
            "🎯 Filtrar por probabilidad (+1.5 FT):",
            ["Todos los partidos", "Mayor o igual a 85%", "Mayor o igual a 75%"]
        )
        
    with f_col3:
        ordenar_por = st.selectbox("↕️ Ordenar resultados por:", ["Hora (EC)", "+1.5 FT (%)", "+0.5 HT (%)"])

    # Aplicar Filtro de Búsqueda
    if busqueda_equipo:
        df = df[df["Partido"].str.contains(busqueda_equipo, case=False, na=False)]

    # Aplicar Filtro de Probabilidad
    if filtro_probabilidad == "Mayor o igual a 85%":
        df = df[df["+1.5 FT (%)"] >= 85]
    elif filtro_probabilidad == "Mayor o igual a 75%":
        df = df[df["+1.5 FT (%)"] >= 75]

    # Ordenar Datos
    if ordenar_por == "+1.5 FT (%)":
        df = df.sort_values(by="+1.5 FT (%)", ascending=False)
    elif ordenar_por == "+0.5 HT (%)":
        df = df.sort_values(by="+0.5 HT (%)", ascending=False)
    else:
        df = df.sort_values(by="Hora (EC)", ascending=True)

    st.markdown(f"**Partidos mostrados:** `{len(df)}`")

    # --- DESPLEGABLES POR LIGA (EXPANDERS) ---
    ligas_unicas = df["Liga"].unique()
    
    if len(ligas_unicas) == 0:
        st.info("No hay partidos que coincidan con los filtros seleccionados.")
    else:
        for liga in ligas_unicas:
            df_liga = df[df["Liga"] == liga]
            
            # Formato desplegable por Liga
            with st.expander(f"🏆 {liga} ({len(df_liga)} partido/s)"):
                df_mostrar = df_liga.drop(columns=["Liga", "Local", "Visitante"])
                
                # Dar formato visual de porcentaje en la tabla
                df_mostrar["+0.5 HT (%)"] = df_mostrar["+0.5 HT (%)"].astype(str) + "%"
                df_mostrar["+1.5 FT (%)"] = df_mostrar["+1.5 FT (%)"].astype(str) + "%"
                df_mostrar["AA (%)"] = df_mostrar["AA (%)"].astype(str) + "%"
                
                st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
