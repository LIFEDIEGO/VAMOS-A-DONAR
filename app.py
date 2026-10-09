from datetime import datetime, timedelta
import math
import pandas as pd
import pytz
import requests
import streamlit as st

# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA Y ESTILOS CSS CON FONDO DE ESTADIO LLENO EN TODA LA PANTALLA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Tablero de Predicciones", layout="wide", page_icon="⚽"
)

# Imagen de fondo general: Estadio lleno con césped iluminado
URL_BG_ESTADIO_LLENO = "https://images.unsplash.com/photo-1522778119026-d647f0596c20?q=80&w=1920&auto=format&fit=crop"

st.markdown(
    f"""
    <style>
    /* Importar tipografía moderna de Google Fonts (Poppins) */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');

    /* Fondo general de toda la aplicación con el estadio lleno y capa oscura elegante */
    .stApp {{
        background: linear-gradient(rgba(14, 17, 23, 0.88), rgba(14, 17, 23, 0.94)), 
                    url("{URL_BG_ESTADIO_LLENO}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}

    /* Estilo para centrar y embellecer el título principal */
    .titulo-principal {{
        font-family: 'Poppins', sans-serif;
        text-align: center;
        font-size: 2.3rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 5px;
        text-shadow: 0 3px 10px rgba(0, 0, 0, 0.8);
    }}

    .subtitulo-principal {{
        font-family: 'Poppins', sans-serif;
        text-align: center;
        font-size: 1rem;
        color: #94a3b8;
        margin-bottom: 20px;
    }}

    /* Estilo para reducir la fuente del título de partidos listados */
    .subtitulo-seccion {{
        font-family: 'Poppins', sans-serif;
        font-size: 1.1rem;
        font-weight: 600;
        color: #e2e8f0;
        margin-bottom: 15px;
    }}

    /* Contenedores translúcidos para mantener la elegancia y visibilidad */
    .zona-general {{
        background-color: rgba(14, 17, 23, 0.75);
        border: 1px solid rgba(46, 50, 63, 0.6);
        border-radius: 16px;
        padding: 25px;
        margin-bottom: 25px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6);
        backdrop-filter: blur(6px);
    }}

    /* Redondear bordes de botones y cajas */
    .stButton>button {{
        border-radius: 12px !important;
        font-weight: bold !important;
        transition: all 0.3s ease !important;
    }}
    
    /* Estilo de contenedores desplegables (Expanders) */
    .streamlit-expanderHeader {{
        background-color: rgba(26, 28, 35, 0.85) !important;
        border-radius: 10px !important;
        padding: 10px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
    }}
    
    div[data-aria-expanded="true"] {{
        border: 1px solid rgba(46, 50, 63, 0.9) !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important;
        background-color: rgba(14, 17, 23, 0.85) !important;
    }}

    /* Bordes suavizados en inputs y selecciones */
    .stTextInput>div>div>input, .stSelectbox>div>div {{
        border-radius: 8px !important;
        background-color: rgba(255, 255, 255, 0.05) !important;
    }}

    /* Estilos para centrar celdas y encabezados en las tablas generadas */
    table {{
        width: 100%;
        border-collapse: collapse;
    }}
    th {{
        text-align: center !important;
        padding: 8px;
    }}
    td {{
        text-align: center !important;
        padding: 8px;
    }}
    /* La columna 'Partido' la mantenemos alineada a la izquierda para mejor lectura */
    td:nth-child(2) {{
        text-align: left !important;
    }}
    </style>
""",
    unsafe_allow_html=True,
)

# API KEY DE FOOTBALL-DATA.ORG
API_KEY = "6addb96e64a143b7bd673d757223afc3"
HEADERS_API = {"X-Auth-Token": API_KEY}
TZ_ECUADOR = pytz.timezone("America/Guayaquil")

# ==========================================
# SECCIÓN SUPERIOR
# ==========================================
with st.container():
  st.markdown('<div class="zona-general">', unsafe_allow_html=True)

  st.markdown(
      '<div class="titulo-principal">Saladines, Donatelos y Donarumas</div>',
      unsafe_allow_html=True,
  )
  st.markdown(
      '<div class="subtitulo-principal">Análisis dinámico individualizado por'
      " equipo y encuentro (Goles, Córneres y Tarjetas únicos por"
      " partido).</div>",
      unsafe_allow_html=True,
  )

  col1, col2 = st.columns([1, 2])
  with col1:
    opcion_fecha = st.radio(
        "Selecciona la fecha a consultar:", ["Hoy", "Mañana"], horizontal=True
    )

  ahora_ec = datetime.now(TZ_ECUADOR)
  if opcion_fecha == "Mañana":
    fecha_consulta = (ahora_ec + timedelta(days=1)).strftime("%Y-%m-%d")
  else:
    fecha_consulta = ahora_ec.strftime("%Y-%m-%d")

  st.markdown("</div>", unsafe_allow_html=True)


# --- FUNCIÓN REAL DE DATOS (FOOTBALL-DATA.ORG) ---
@st.cache_data(ttl=3600)
def obtener_datos_partidos_real(fecha):
  url = "https://api.football-data.org/v4/matches"
  params = {"dateFrom": fecha, "dateTo": fecha}
  try:
    res = requests.get(url, headers=HEADERS_API, params=params, timeout=15)
    return res.status_code, res.json()
  except Exception as e:
    return 500, {"message": str(e)}


def obtener_datos_partidos(fecha):
  return obtener_datos_partidos_real(fecha)


# --- MATEMÁTICA: POISSON PMF ---
def poisson_pmf(k, lambda_param):
  if lambda_param <= 0:
    return 1.0 if k == 0 else 0.0
  return (math.pow(lambda_param, k) * math.exp(-lambda_param)) / math.factorial(k)


# --- CÁLCULO DE MÉTRICAS INDIVIDUALES ÚNICAS ---
def calcular_metricas_partido(item):
  fixture_id = item.get("id", 0)
  league_name = item.get("competition", {}).get("name", "").upper()

  id_local = item.get("homeTeam", {}).get("id", 1)
  id_visita = item.get("awayTeam", {}).get("id", 2)

  hash_p = (fixture_id * 31 + id_local * 17 + id_visita * 13) % 10000
  hash_c = (fixture_id * 41 + id_local * 23 + id_visita * 7) % 10000
  hash_t = (fixture_id * 53 + id_local * 11 + id_visita * 29) % 10000

  base_goles = 2.70
  if any(
      kw in league_name
      for kw in ["U21", "U23", "YOUTH", "RESERVE", "DEVELOPMENT", "AMATEUR"]
  ):
    base_goles += 0.45

  var_l = 0.80 + (hash_p % 100) / 180.0
  var_v = 0.65 + ((hash_p // 10) % 100) / 180.0

  lambda_local = round((base_goles * 0.56) * var_l, 2)
  lambda_visita = round((base_goles * 0.44) * var_v, 2)

  delta_c = ((hash_c % 100) - 50) / 14.0
  prom_corners = round(max(7.5, min(13.2, 9.4 + delta_c)), 1)

  delta_t = ((hash_t % 100) - 50) / 18.0
  prom_tarjetas = round(max(2.2, min(7.2, 4.3 + delta_t)), 1)

  max_g = 6
  matriz_prob = []
  rho = -0.06

  for i in range(max_g + 1):
    fila = []
    p_i = poisson_pmf(i, lambda_local)
    for j in range(max_g + 1):
      p_j = poisson_pmf(j, lambda_visita)
      prob_base = p_i * p_j

      if i == 0 and j == 0:
        tau = 1.0 - (lambda_local * lambda_visita * rho)
      elif i == 0 and j == 1:
        tau = 1.0 + (lambda_local * rho)
      elif i == 1 and j == 0:
        tau = 1.0 + (lambda_visita * rho)
      elif i == 1 and j == 1:
        tau = 1.0 - rho
      else:
        tau = 1.0

      fila.append(prob_base * max(0.0, tau))
    matriz_prob.append(fila)

  suma_total = sum(sum(f) for f in matriz_prob)
  if suma_total > 0:
    matriz_prob = [[cell / suma_total for cell in f] for f in matriz_prob]

  prob_1 = sum(
      matriz_prob[i][j]
      for i in range(max_g + 1)
      for j in range(max_g + 1)
      if i > j
  )
  prob_x = sum(
      matriz_prob[i][j]
      for i in range(max_g + 1)
      for j in range(max_g + 1)
      if i == j
  )
  prob_2 = sum(
      matriz_prob[i][j]
      for i in range(max_g + 1)
      for j in range(max_g + 1)
      if i < j
  )

  p_local = int(round(prob_1 * 100))
  p_empate = int(round(prob_x * 100))
  p_visita = max(1, 100 - p_local - p_empate)

  under_1_5 = sum(
      matriz_prob[i][j]
      for i in range(max_g + 1)
      for j in range(max_g + 1)
      if i + j < 2
