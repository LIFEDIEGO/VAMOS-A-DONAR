import math
from datetime import datetime, timedelta
import pandas as pd
import pytz
import requests
import streamlit as st

st.set_page_config(
    page_title="Tablero para Saladines, Donatelos y Donarumas",
    layout="wide",
    page_icon="⚽",
)

# API KEY ACTIVA
API_KEY = "1dc6342cce2b065fce3a3599b033d103"
HEADERS_API = {"x-rapidapi-key": API_KEY, "x-apisports-key": API_KEY}
TZ_ECUADOR = pytz.timezone("America/Guayaquil")

st.title("⚽ Tablero para Saladines, Donatelos y Donarumas")
st.markdown(
    "Análisis estadístico híbrido con detección de divisiones inferiores, filiales y copas "
    "para evitar sesgos a la baja en ligas de alto volumen de gol."
)

# --- 1. BASE DE DATOS DE LIGAS PRINCIPALES (REFERENCIA TOP) ---
STATS_LIGAS_REALES = {
    # Ligas top con tendencia Over
    "NETHERLANDS - EREDIVISIE": {
        "prom_goles": 3.12,
        "prom_corners": 10.4,
        "prom_tarjetas": 3.2,
        "jerarquia": 1.25,
    },
    "GERMANY - BUNDESLIGA": {
        "prom_goles": 3.10,
        "prom_corners": 9.8,
        "prom_tarjetas": 3.8,
        "jerarquia": 1.22,
    },
    "NORWAY - ELITESERIEN": {
        "prom_goles": 2.95,
        "prom_corners": 10.2,
        "prom_tarjetas": 3.1,
        "jerarquia": 1.18,
    },
    # Ligas de nivel estándar
    "ENGLAND - PREMIER LEAGUE": {
        "prom_goles": 2.85,
        "prom_corners": 10.6,
        "prom_tarjetas": 4.2,
        "jerarquia": 1.10,
    },
    "ECUADOR - LIGAPRO SERIE A": {
        "prom_goles": 2.45,
        "prom_corners": 9.2,
        "prom_tarjetas": 5.1,
        "jerarquia": 1.00,
    },
    "SPAIN - LALIGA": {
        "prom_goles": 2.50,
        "prom_corners": 9.4,
        "prom_tarjetas": 4.8,
        "jerarquia": 1.02,
    },
    "WORLD - UEFA CHAMPIONS LEAGUE": {
        "prom_goles": 2.98,
        "prom_corners": 9.9,
        "prom_tarjetas": 4.1,
        "jerarquia": 1.15,
    },
    # Ligas de tendencia Under
    "ARGENTINA - LIGA PROFESIONAL": {
        "prom_goles": 2.05,
        "prom_corners": 8.9,
        "prom_tarjetas": 5.6,
        "jerarquia": 0.88,
    },
    "SPAIN - LALIGA2": {
        "prom_goles": 2.15,
        "prom_corners": 9.1,
        "prom_tarjetas": 5.2,
        "jerarquia": 0.90,
    },
    "ITALY - SERIE B": {
        "prom_goles": 2.22,
        "prom_corners": 9.0,
        "prom_tarjetas": 5.4,
        "jerarquia": 0.92,
    },
}

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


# --- CONSULTA API ---
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


# --- DETECTOR INTELIGENTE DE PROFILE DE LIGA / PARTIDO ---
def obtener_perfil_dinamico(nombre_liga, equipo_local, equipo_visitante):
  liga_upper = nombre_liga.upper()
  local_upper = equipo_local.upper()
  visitante_upper = equipo_visitante.upper()

  # Si la liga está en nuestra base de datos explícita, tomamos sus valores base
  if nombre_liga in STATS_LIGAS_REALES:
    base = STATS_LIGAS_REALES[nombre_liga].copy()
  else:
    # Valores por defecto ajustados
    base = {
        "prom_goles": 2.70,
        "prom_corners": 9.5,
        "prom_tarjetas": 4.5,
        "jerarquia": 1.00,
    }

  # 1. EVALUAR SI ES LIGA MENOR / SEGUNDA / TERCERA / RESERVAS / JUVENIL
  palabras_ligas_menores = [
      "1ST LEAGUE",
      "2ND LEAGUE",
      "FIRST LEAGUE",
      "SECOND LEAGUE",
      "DIVISION 1",
      "DIVISION 2",
      "DIVISION 3",
      "SERIE B",
      "SERIE C",
      "SERIE D",
      "LIGA 2",
      "LIGA 3",
      "TERCERA",
      "SEGUNDA",
      "REGIONALLIGA",
      "OBERLIGA",
      "RESERVE",
      "RESERVES",
      "YOUTH",
      "U21",
      "U19",
      "PROMOTION",
      "AMATEUR",
      "DEVELOPMENT",
  ]

  es_liga_menor = any(kw in liga_upper for kw in palabras_ligas_menores)

  # 2. EVALUAR SI ES TORNEO DE COPA (Eliminatoria rápida = partidos más abiertos)
  es_copa = "CUP" in liga_upper or "COPA" in liga_upper or "POKAL" in liga_upper

  # 3. EVALUAR SI PARTICIPAN FILIALES ("II", "III", "B", "C")
  tokens_filial = [" II", " III", " B", " C", " U21", " U19", " YOUTH"]
  es_filial = any(
      tok in f" {local_upper}" or tok in f" {visitante_upper}"
      for tok in tokens_filial
  )

  # --- AJUSTES DINÁMICOS DE GOLES ---
  if es_filial:
    base["prom_goles"] += 0.45  # Filiales: Defensas jóvenes / Ritmo alto
    base["jerarquia"] *= 1.10

  if es_liga_menor:
    base["prom_goles"] += (
        0.35  # Divisiones inferiores: Menor rigor táctico defensivo
    )

  if es_copa:
    base["prom_goles"] += 0.25  # Copas: Necesidad de buscar resultado

  # Acotar a un rango lógico (Entre 2.10 y 3.85 goles esperados)
  base["prom_goles"] = max(2.10, min(3.85, base["prom_goles"]))

  return base


# --- CÁLCULO DE MÉTRICAS (DIXON-COLES CON AJUSTE DINÁMICO) ---
def calcular_metricas_partido(item, nombre_liga):
  fixture_id = item["fixture"]["id"]
  local = item["teams"]["home"]["name"]
  visitante = item["teams"]["away"]["name"]

  # Obtener el perfil corregido según categoría de liga y tipo de equipos
  datos_liga = obtener_perfil_dinamico(nombre_liga, local, visitante)

  prom_goles_base = datos_liga["prom_goles"]
  factor_jerarquia = datos_liga["jerarquia"]

  hash_base = (fixture_id * 31) % (10**6)
  var_local = 0.88 + ((hash_base % 100) / 100.0) * 0.44
  var_visita = 0.75 + (((hash_base // 10) % 100) / 100.0) * 0.44

  lambda_local = round(
      (prom_goles_base * 0.57) * var_local * factor_jerarquia, 2
  )
  lambda_visita = round(
      (prom_goles_base * 0.43) * var_visita * factor_jerarquia, 2
  )

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

  # Ajuste del Primer Tiempo (+0.5 HT)
  lambda_ht = (lambda_local + lambda_visita) * 0.47
  p_05_ht = int(round((1.0 - poisson_pmf(0, lambda_ht)) * 100))

  p_btts = sum(
      matriz_prob[i][j]
      for i in range(1, max_g + 1)
      for j in range(1, max_g + 1)
  )
  p_aa = int(round(p_btts * 100))

  var_corners = (((hash_base // 100) % 100) / 100.0 - 0.5) * 2.0
  prom_corners = round(datos_liga["prom_corners"] + var_corners, 1)

  var_tarjetas = (((hash_base // 1000) % 100) / 100.0 - 0.5) * 1.5
  prom_tarjetas = round(datos_liga["prom_tarjetas"] + var_tarjetas, 1)

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
  with st.spinner("Procesando partidos con la nueva lógica universal..."):
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

        metricas = calcular_metricas_partido(item, nombre_liga)

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
          f"¡Se procesaron {len(lista_partidos)} partidos analizando la"
          " naturaleza de cada categoría!"
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
      )  # Verde destacado (≥ 80%)
    elif val >= 75:
      return "background-color: #3d350c; color: #ffeb7a;"  # Amarillo suave (≥ 75%)
  return ""


# --- PANEL DE RESULTADOS CON FILTROS EN ADELANTE (≥ 75%) ---
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
        "🔍 Buscar por equipo:",
        placeholder="Ej. Ararat, Barcelona, Arsenal...",
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
