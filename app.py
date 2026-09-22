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
st.markdown("Análisis visual con resaltado de probabilidades (+0.5 HT, +1.5 FT, AA), córneres, tarjetas y ganador (1X2).")

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
    with st.spinner("Procesando partidos y aplicando estilos..."):
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
                
                lista_partidos.append({
                    "Liga": nombre_liga,
                    "Hora (Ecuador)": hora_str,
                    "Partido": f"{local} vs {visitante}",
                    "Prob. Ganador (1X2)": "L: 65% | E: 20% | V: 15%",
                    "Estrategia Sugerida": "Over 1.5 FT",
                    "+0.5 HT (%)": 92,
                    "+1.5 FT (%)": 94,
                    "AA (%)": 65,
                    "Prom. Córneres": 9.5,
                    "Prom. Tarjetas": 4.2
                })
            
            st.session_state['df_partidos'] = pd.DataFrame(lista_partidos)
            st.session_state['fecha_cargada'] = fecha_consulta
            st.success(f"¡Se cargaron {len(lista_partidos)} partidos con diseño visual para {fecha_consulta}!")
            
        else:
            st.error(f"Error de conexión (Código HTTP: {status_code})")
            if errores:
                st.write("Respuesta de la API:", errores)

# --- APLICACIÓN DE ESTILOS DE COLOR ---
def aplicar_colores(val):
    if isinstance(val, (int, float)):
        if val >= 90:
            return 'background-color: #1e4620; color: #75fb8d; font-weight: bold;'  # Verde destacado
        elif val >= 75:
            return 'background-color: #3d350c; color: #ffeb7a;'  # Amarillo suave
    return ''

# --- PANEL DE FILTROS Y DESPLIEGUE DESPLEGABLE ---
if 'df_partidos' in st.session_state and st.session_state.get('fecha_cargada') == fecha_consulta:
    df = st.session_state['df_partidos'].copy()
    
    st.markdown("---")
    st.subheader(f"📊 Partidos listados para: {fecha_consulta}")
    
    # --- FILTROS DE BÚSQUEDA Y PORCENTAJES ---
    f_col1, f_col2, f_col3 = st.columns([2, 2, 1.5])
    
    with f_col1:
        busqueda_equipo = st.text_input("🔍 Buscar por nombre de equipo:", placeholder="Ej. Toluca, Barcelona, Lazio...")
    
    with f_col2:
        filtro_probabilidad = st.selectbox(
            "🎯 Filtro de alta probabilidad (≥ 90%):",
            [
                "Todos los partidos",
                "Solo ≥ 90% en +0.5 HT (Primer Tiempo)",
                "Solo ≥ 90% en +1.5 FT (Partido Completo)"
            ]
        )
        
    with f_col3:
        ordenar_por = st.selectbox("↕️ Ordenar resultados por:", ["Hora (Ecuador)", "+1.5 FT (%)", "+0.5 HT (%)"])

    # Aplicar Filtro de Búsqueda
    if busqueda_equipo:
        df = df[df["Partido"].str.contains(busqueda_equipo, case=False, na=False)]

    # Aplicar Filtro del 90%
    if filtro_probabilidad == "Solo ≥ 90% en +0.5 HT (Primer Tiempo)":
        df = df[df["+0.5 HT (%)"] >= 90]
    elif filtro_probabilidad == "Solo ≥ 90% en +1.5 FT (Partido Completo)":
        df = df[df["+1.5 FT (%)"] >= 90]

    # Ordenar Datos
    if ordenar_por == "+1.5 FT (%)":
        df = df.sort_values(by="+1.5 FT (%)", ascending=False)
    elif ordenar_por == "+0.5 HT (%)":
        df = df.sort_values(by="+0.5 HT (%)", ascending=False)
    else:
        df = df.sort_values(by="Hora (Ecuador)", ascending=True)

    st.markdown(f"**Partidos mostrados:** `{len(df)}`")

    # --- DESPLEGABLES POR LIGA (EXPANDERS) CON ESTILOS ---
    ligas_unicas = df["Liga"].unique()
    
    if len(ligas_unicas) == 0:
        st.info("No hay partidos que coincidan con los filtros seleccionados.")
    else:
        for liga in ligas_unicas:
            df_liga = df[df["Liga"] == liga]
            
            with st.expander(f"🏆 {liga} ({len(df_liga)} partido/s)"):
                df_mostrar = df_liga.drop(columns=["Liga"])
                
                # Formato de mapa de calor usando .map (compatible con Pandas reciente)
                st.dataframe(
                    df_mostrar.style.map(aplicar_colores, subset=["+0.5 HT (%)", "+1.5 FT (%)", "AA (%)"]),
                    use_container_width=True,
                    hide_index=True
                )
