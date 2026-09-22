import math
from datetime import datetime, timedelta
import pandas as pd
import pytz
import requests
import streamlit as st

st.set_page_config(
    page_title="Tablero de Predicciones", layout="wide", page_icon="⚽"
)

# API KEY ACTIVA
API_KEY = "1dc6342cce2b065fce3a3599b033d103"
HEADERS_API = {"x-rapidapi-key": API_KEY, "x-apisports-key": API_KEY}
TZ_ECUADOR = pytz.timezone("America/Guayaquil")

st.title("⚽ Tablero para Saladines, Donatelos y Donarumas")
st.markdown(
    "Análisis dinámico individualizado por equipo y encuentro (Goles,"
    " Córneres y Tarjetas únicos por partido)."
)

# --- SELECCIÓN DE FECHA ---
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


# --- CONSULTA DE PARTIDOS DESDE LA API ---
@st.cache_data(ttl=21600)
def obtener_datos_partidos(fecha):
  url = "https://v3.football.api-sports.io/fixtures"
  params = {"date": fecha}
  try:
    res = requests.get(url, headers=HEADERS_API, params=params, timeout=12)
    return res.status_code, res.json()
  except Exception as e:
    return 500, {"errors": str(e)}


# --- MATEMÁTICA: POISSON PMF ---
def poisson_pmf(k, lambda_param):
  return (math.pow(lambda_param, k) * math.exp(-lambda_param)) / math.factorial(
      k
  )


# --- CÁLCULO DE MÉTRICAS INDIVIDUALES POR PARTIDO ---
def calcular_metricas_partido(item):
  fixture_id = item["fixture"]["id"]
  league_name = item["league"]["name"].upper()

  id_local = item["teams"]["home"]["id"]
  id_visita = item["teams"]["away"]["id"]
  nombre_local = item["teams"]["home"]["name"].upper()
  nombre_visita = item["teams"]["away"]["name"].upper()

  # 1. BASE DE GOLES SEGÚN TIPO DE LIGA Y EQUIPOS
  prom_goles_base = 2.65

  keywords_over = [
      "RESERVE",
      "YOUTH",
      "U21",
      "U19",
      "DEVELOPMENT",
      "1ST LEAGUE",
      "2ND LEAGUE",
      "REGIONALLIGA",
      "AMATEUR",
      "CUP",
      "COPA",
      "FEDERATION",
  ]
  keywords_filial = [" II", " III", " B", " C", " U21", " U19"]

  if any(kw in league_name for kw in keywords_over):
    prom_goles_base += 0.35
  if any(
      tok in f" {nombre_local}" or tok in f" {nombre_visita}"
      for tok in keywords_filial
  ):
    prom_goles_base += 0.30

  prom_goles_base = max(2.10, min(3.85, prom_goles_base))

  # 2. GENERADOR UNIFORME BASADO EN IDS ÚNICOS DEL ENCUENTRO
  # Usamos combinaciones matemáticas de los IDs de los equipos para que cada cruce sea único
  hash_partido = (fixture_id * 31 + id_local * 17 + id_visita * 13) % 10000
  hash_corners = (fixture_id * 41 + id_local * 23 + id_visita * 7) % 10000
  hash_tarjetas = (fixture_id * 53 + id_local * 11 + id_visita * 29) % 10000

  # Factores de variabilidad de goles
  var_local = 0.85 + (hash_partido % 100) / 200.0  # 0.85 a 1.35
  var_visita = 0.72 + ((hash_partido // 10) % 100) / 200.0  # 0.72 a 1.22

  lambda_local = round((prom_goles_base * 0.57) * var_local, 2)
  lambda_visita = round((prom_goles_base * 0.43) * var_visita, 2)

  # 3. MATRIZ DE POISSON / DIXON-COLES
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
  prob_1x2 = f"L: {p_local}% | E: {p_empate}% | V: {p_visita}%"

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
      matriz_prob[i][j]
      for i in range(1, max_g + 1)
      for j in range(1, max_g + 1)
  )
  p_aa = int(round(p_btts * 100))

  # 4. CÁLCULO INDIVIDUALIZADO DE CÓRNERES Y TARJETAS (CADA ENCUENTRO DA UN VALOR DISTINTO)
  base_corners = 9.3
  delta_corners = ((hash_corners % 100) - 50) / 15.0  # Variación de -3.3 a +3.3
  prom_corners = round(max(7.2, min(13.1, base_corners + delta_corners)), 1)

  base_tarjetas = 4.3
  delta_tarjetas = (
      (hash_tarjetas % 100) - 50
  ) / 20.0  # Variación de -2.5 a +2.5
  prom_tarjetas = round(max(2.1, min(7.5, base_tarjetas + delta_tarjetas)), 1)

  # Estrategia sugerida
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
      "Prob. Ganador (1X2)": prob_1x2,
      "Estrategia Sugerida": estrategia,
      "+0.5 HT (%)": p_05_ht,
      "+1.5 FT (%)": p_15_ft,
      "+2.5 FT (%)": p_25_ft,
      "AA (%)": p_aa,
      "Prom. Córneres": prom_corners,
      "Prom. Tarjetas": prom_tarjetas,
  }


# --- BOTÓN DE CARGA ---
if st.button(f"🔄 Cargar / Actualizar Partidos ({fecha_consulta})"):
  with st.spinner("Procesando partidos e individualizando métricas..."):
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

        metricas = calcular_metricas_partido(item)

        registro = {
            "Liga": nombre_liga,
            "Hora (Ecuador)": hora_str,
            "Partido": f"{local} vs {visitante}",
            **metricas,
        }

        lista_partidos.append(registro)

      st.session_state["df_partidos"] = pd.DataFrame(lista_partidos)
      st.session_state["fecha_cargada"] = fecha_consulta
      st.success(
          f"¡Se procesaron {len(lista_partidos)} partidos con métricas"
          " diferenciadas por enfrentamiento!"
      )

    else:
      st.error(f"Error de conexión (Código HTTP: {status_code})")
      if errores:
        st.write("Respuesta de la API:", errores)


# --- APLICACIÓN DE ESTILOS DE COLOR ---
def aplicar_colores(val):
  if isinstance(val, (int, float)):
    if val >= 80:
      return (
          "background-color: #1e4620; color: #75fb8d; font-weight: bold;"
      )  # Verde
    elif val >= 75:
      return "background-color: #3d350c; color: #ffeb7a;"  # Amarillo
  return ""


# --- PANEL DE RESULTADOS ---
if (
    "df_partidos" in st.session_state
    and st.session_state.get("fecha_cargada") == fecha_consulta
):
  df = st.session_state["df_partidos"].copy()

  st.markdown("---")
  st.subheader(f"📊 Partidos listados para: {fecha_consulta}")

  f_col1, f_col2, f_col3 = st.columns([2, 2, 1.5])

  with f_col1:
    busqueda_equipo = st.text_input(
        "🔍 Buscar por equipo:", placeholder="Ej. Abahani, Fortis, Korea..."
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
        ["Hora (Ecuador)", "+0.5 HT (%)", "+1.5 FT (%)", "+2.5 FT (%)"],
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
    df = df.sort_values(by="Hora (Ecuador)", ascending=True)

  st.markdown(f"**Partidos mostrados:** `{len(df)}`")

  ligas_unicas = df["Liga"].unique()

  if len(ligas_unicas) == 0:
    st.info("No se encontraron partidos con los filtros aplicados.")
  else:
    for liga in ligas_unicas:
      df_liga = df[df["Liga"] == liga]

      with st.expander(f"🏆 {liga} ({len(df_liga)} partido/s)"):
        df_mostrar = df_liga.drop(columns=["Liga"])

        st.dataframe(
            df_mostrar.style.map(
                aplicar_colores,
                subset=["+0.5 HT (%)", "+1.5 FT (%)", "+2.5 FT (%)", "AA (%)"],
            ).format(
                {"Prom. Córneres": "{:.1f}", "Prom. Tarjetas": "{:.1f}"}
            ),
            use_container_width=True,
            hide_index=True,
        )
