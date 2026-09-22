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
    /* La columna 'Partido' la mantenemos alineada a la izquierda para mejor lectura de equipos */
    td:nth-child(2) {{
        text-align: left !important;
    }}
    </style>
""",
    unsafe_allow_html=True,
)

# API KEY (En modo de prueba temporal)
API_KEY = "1dc6342cce2b065fce3a3599b033d103"
HEADERS_API = {"x-rapidapi-key": API_KEY, "x-apisports-key": API_KEY}
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


# --- FUNCIÓN TEMPORAL DE PRUEBA (MOCK DATA) ---
def obtener_datos_partidos_prueba(fecha):
  datos_falsos = {
      "errors": {},
      "response": [
          {
              "fixture": {
                  "id": 101,
                  "date": f"{fecha}T15:00:00+00:00",
                  "status": {"short": "NS", "elapsed": 0},
              },
              "league": {
                  "id": 39,
                  "name": "Premier League",
                  "country": "England",
                  "season": 2026,
              },
              "teams": {
                  "home": {
                      "id": 40,
                      "name": "Liverpool",
                      "logo": (
                          "https://media.api-sports.io/football/teams/40.png"
                      ),
                  },
                  "away": {
                      "id": 42,
                      "name": "Arsenal",
                      "logo": (
                          "https://media.api-sports.io/football/teams/42.png"
                      ),
                  },
              },
              "goals": {"home": None, "away": None},
          },
          {
              "fixture": {
                  "id": 102,
                  "date": f"{fecha}T17:30:00+00:00",
                  "status": {"short": "NS", "elapsed": 0},
              },
              "league": {
                  "id": 39,
                  "name": "Premier League",
                  "country": "England",
                  "season": 2026,
              },
              "teams": {
                  "home": {
                      "id": 33,
                      "name": "Manchester United",
                      "logo": (
                          "https://media.api-sports.io/football/teams/33.png"
                      ),
                  },
                  "away": {
                      "id": 50,
                      "name": "Manchester City",
                      "logo": (
                          "https://media.api-sports.io/football/teams/50.png"
                      ),
                  },
              },
              "goals": {"home": None, "away": None},
          },
          {
              "fixture": {
                  "id": 103,
                  "date": f"{fecha}T20:00:00+00:00",
                  "status": {"short": "NS", "elapsed": 0},
              },
              "league": {
                  "id": 140,
                  "name": "La Liga",
                  "country": "Spain",
                  "season": 2026,
              },
              "teams": {
                  "home": {
                      "id": 529,
                      "name": "Barcelona",
                      "logo": (
                          "https://media.api-sports.io/football/teams/529.png"
                      ),
                  },
                  "away": {
                      "id": 541,
                      "name": "Real Madrid",
                      "logo": (
                          "https://media.api-sports.io/football/teams/541.png"
                      ),
                  },
              },
              "goals": {"home": None, "away": None},
          },
      ],
  }
  return 200, datos_falsos


def obtener_datos_partidos(fecha):
  return obtener_datos_partidos_prueba(fecha)


# --- MATEMÁTICA: POISSON PMF ---
def poisson_pmf(k, lambda_param):
  if lambda_param <= 0:
    return 1.0 if k == 0 else 0.0
  return (math.pow(lambda_param, k) * math.exp(-lambda_param)) / math.factorial(k)


# --- CÁLCULO DE MÉTRICAS INDIVIDUALES ÚNICAS ---
def calcular_metricas_partido(item):
  fixture_id = item["fixture"]["id"]
  league_name = item["league"]["name"].upper()

  id_local = item["teams"]["home"]["id"]
  id_visita = item["teams"]["away"]["id"]

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
  )
  under_2_5 = sum(
      matriz_prob[i][j]
      for i in range(max_g + 1)
      for j in range(max_g + 1)
      if i + j < 3
  )

  p_15_ft = int(round((1.0 - under_1_5) * 100))
  p_25_ft = int(round((1.0 - under_2_5) * 100))

  lambda_ht = (lambda_local + lambda_visita) * 0.46
  p_05_ht = int(round((1.0 - poisson_pmf(0, lambda_ht)) * 100))

  p_btts = sum(
      matriz_prob[i][j] for i in range(1, max_g + 1) for j in range(1, max_g + 1)
  )
  p_aa = int(round(p_btts * 100))

  if p_25_ft >= 75:
    estrategia = "Over 2.5 FT"
  elif p_15_ft >= 80:
    estrategia = "Over 1.5 FT"
  elif p_05_ht >= 75:
    estrategia = "Over 0.5 HT"
  elif p_local >= 60:
    estrategia = "Gana Local (1)"
  elif p_aa >= 65:
    estrategia = "Ambos Anotan (AA)"
  else:
    estrategia = "Gana / Empata Local"

  return {
      "% Local": p_local,
      "% Empate": p_empate,
      "% Visita": p_visita,
      "Estrategia Sugerida": estrategia,
      "+0.5 HT (%)": p_05_ht,
      "+1.5 FT (%)": p_15_ft,
      "+2.5 FT (%)": p_25_ft,
      "AA (%)": p_aa,
      "Prom. Córneres": prom_corners,
      "Prom. Tarjetas": prom_tarjetas,
  }


# Botón de carga
if st.button(f"🔄 Cargar / Actualizar Partidos ({fecha_consulta})"):
  with st.spinner("Procesando datos de prueba y probabilidades..."):
    status_code, respuesta = obtener_datos_partidos(fecha_consulta)

    errores = respuesta.get("errors", {})
    datos = respuesta.get("response", [])

    if status_code == 200 and not errores and datos:
      lista_partidos = []

      for item in datos:
        nombre_liga = (
            f"{item['league']['country'].upper()} -"
            f" {item['league']['name'].upper()}"
        )

        fecha_utc = datetime.fromisoformat(
            item["fixture"]["date"].replace("Z", "+00:00")
        )
        fecha_ec = fecha_utc.astimezone(TZ_ECUADOR)
        hora_str = fecha_ec.strftime("%H:%M")

        local = item["teams"]["home"]["name"]
        visitante = item["teams"]["away"]["name"]

        logo_local = item["teams"]["home"]["logo"]
        logo_visita = item["teams"]["away"]["logo"]

        metricas = calcular_metricas_partido(item)

        partido_con_escudos = (
            f"<div style='display: flex; align-items: center; gap: 8px;'>"
            f"<img src='{logo_local}' width='18' height='18' style='vertical-align: middle;'/>"
            f"<span>{local}</span>"
            f"<span style='color: #94a3b8; margin: 0 4px;'>vs</span>"
            f"<img src='{logo_visita}' width='18' height='18' style='vertical-align: middle;'/>"
            f"<span>{visitante}</span>"
            f"</div>"
        )

        registro = {
            "Hora": hora_str,
            "Partido": partido_con_escudos,
            **metricas,
            "Liga_Oculta": nombre_liga,
        }

        lista_partidos.append(registro)

      st.session_state["df_partidos"] = pd.DataFrame(lista_partidos)
      st.session_state["fecha_cargada"] = fecha_consulta
      st.success(
          f"¡Se procesaron {len(lista_partidos)} partidos de prueba con éxito!"
      )

    else:
      st.error(f"Error de conexión (Código HTTP: {status_code})")


# --- APLICACIÓN DE ESTILOS DE COLOR ---
def aplicar_colores(val):
  if isinstance(val, (int, float)):
    if val >= 80:
      return (
          "background-color: #1e4620; color: #75fb8d; font-weight: bold;"
      )
    elif val >= 75:
      return "background-color: #3d350c; color: #ffeb7a;"
  return ""


# ==========================================
# SECCIÓN INFERIOR (FILTROS Y PARTIDOS)
# ==========================================
if (
    "df_partidos" in st.session_state
    and st.session_state.get("fecha_cargada") == fecha_consulta
):
  df = st.session_state["df_partidos"].copy()

  with st.container():
    st.markdown('<div class="zona-general">', unsafe_allow_html=True)

    st.markdown(
        f"<div class='subtitulo-seccion'>⚽ Partidos listados para:"
        f" {fecha_consulta}</div>",
        unsafe_allow_html=True,
    )

    f_col1, f_col2, f_col3 = st.columns([2, 2, 1.5])

    with f_col1:
      busqueda_equipo = st.text_input(
          "🔍 Buscar por equipo:", placeholder="Ej. Liverpool, Barcelona..."
      )

    with f_col2:
      filtro_probabilidad = st.selectbox(
          "🎯 Filtro de probabilidad (≥ 75%):",
          [
              "Todos los partidos",
              "Solo ≥ 75% en +0.5 HT (Primer Tiempo)",
              "Solo ≥ 80% en +0.5 HT (Primer Tiempo)",
              "Solo ≥ 80% en +1.5 FT (Partido Completo)",
              "Solo ≥ 75% en +2.5 FT (Partido Completo)",
          ],
      )

    with f_col3:
      ordenar_por = st.selectbox(
          "↕️ Ordenar resultados por:",
          ["Hora", "+0.5 HT (%)", "+1.5 FT (%)", "+2.5 FT (%)"],
      )

    if busqueda_equipo:
      df = df[df["Partido"].str.contains(busqueda_equipo, case=False, na=False)]

    if filtro_probabilidad == "Solo ≥ 75% en +0.5 HT (Primer Tiempo)":
      df = df[df["+0.5 HT (%)"] >= 75]
    elif filtro_probabilidad == "Solo ≥ 80% en +0.5 HT (Primer Tiempo)":
      df = df[df["+0.5 HT (%)"] >= 80]
    elif filtro_probabilidad == "Solo ≥ 80% en +1.5 FT (Partido Completo)":
      df = df[df["+1.5 FT (%)"] >= 80]
    elif filtro_probabilidad == "Solo ≥ 75% en +2.5 FT (Partido Completo)":
      df = df[df["+2.5 FT (%)"] >= 75]

    if ordenar_por == "+1.5 FT (%)":
      df = df.sort_values(by="+1.5 FT (%)", ascending=False)
    elif ordenar_por == "+2.5 FT (%)":
      df = df.sort_values(by="+2.5 FT (%)", ascending=False)
    elif ordenar_por == "+0.5 HT (%)":
      df = df.sort_values(by="+0.5 HT (%)", ascending=False)
    else:
      df = df.sort_values(by="Hora", ascending=True)

    st.markdown(f"**Partidos mostrados:** `{len(df)}`")

    ligas_unicas = df["Liga_Oculta"].unique()

    if len(ligas_unicas) == 0:
      st.info("No se encontraron partidos con los filtros aplicados.")
    else:
      for liga in ligas_unicas:
        df_liga = df[df["Liga_Oculta"] == liga]

        with st.expander(f"🏆 {liga} ({len(df_liga)} partido/s)"):
          df_mostrar = df_liga.drop(columns=["Liga_Oculta"])

          st.write(
              df_mostrar.style.map(
                  aplicar_colores,
                  subset=["+0.5 HT (%)", "+1.5 FT (%)", "+2.5 FT (%)", "AA (%)"],
              ).format({
                  "% Local": "{:.0f}%",
                  "% Empate": "{:.0f}%",
                  "% Visita": "{:.0f}%",
                  "Prom. Córneres": "{:.1f}",
                  "Prom. Tarjetas": "{:.1f}",
              }).to_html(escape=False, index=False),
              unsafe_allow_html=True,
          )

    st.markdown("</div>", unsafe_allow_html=True)
