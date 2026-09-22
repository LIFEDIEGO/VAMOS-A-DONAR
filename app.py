import random
from datetime import datetime, timedelta

import pandas as pd
import pytz
import streamlit as st

# =============================================================================
# CONFIGURACIÓN GENERAL
# =============================================================================
st.set_page_config(
    page_title="Tablero de Predicciones", layout="wide", page_icon="⚽"
)

TZ_ECUADOR = pytz.timezone("America/Guayaquil")

# -----------------------------------------------------------------------------
# MODO DE DATOS
# -----------------------------------------------------------------------------
# FASE 1 (actual): datos ficticios generados localmente -> cero consumo de API.
# FASE 2 (siguiente): reemplazar generar_partidos_ficticios() por la conexión
# real (API de fixtures + estadísticas, o una fuente alterna que no consuma
# tokens de la API principal). El resto de la app (filtros, tarjetas, KPIs)
# no debería necesitar cambios porque consume el mismo esquema de columnas.
MODO_DATOS = "ficticio"  # "ficticio" | "real"


# =============================================================================
# ESTILOS (CSS)
# =============================================================================
def inyectar_estilos():
    st.markdown(
        """
        <style>
        .stApp {
            background: #f7f8fb;
        }
        .block-container { padding-top: 1.4rem; padding-bottom: 3rem; }

        /* ---------- HEADER ---------- */
        .header-wrap {
            background: #ffffff;
            border: 1px solid #e7e9f2;
            border-radius: 18px;
            padding: 22px 28px;
            margin-bottom: 18px;
            box-shadow: 0 4px 18px rgba(30,40,80,0.06);
        }
        .header-title {
            font-size: 1.9rem;
            font-weight: 800;
            color: #1b1f2e;
            margin: 0;
            letter-spacing: -0.5px;
        }
        .header-sub {
            color: #6b7188;
            font-size: 0.92rem;
            margin-top: 4px;
        }
        .badge-modo {
            display: inline-block;
            margin-top: 10px;
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.4px;
            background: #fff4d6;
            color: #a3730a;
            border: 1px solid #f0dca3;
        }

        /* ---------- KPI CARDS ---------- */
        .kpi-card {
            background: #ffffff;
            border: 1px solid #e7e9f2;
            border-radius: 14px;
            padding: 14px 16px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(30,40,80,0.04);
        }
        .kpi-value {
            font-size: 1.55rem;
            font-weight: 800;
            color: #1b1f2e;
        }
        .kpi-label {
            font-size: 0.75rem;
            color: #8890a6;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 2px;
        }

        /* ---------- LEAGUE HEADER ---------- */
        .league-title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 1.05rem;
            font-weight: 700;
            color: #1b1f2e;
            margin: 22px 0 10px 0;
            padding-bottom: 6px;
            border-bottom: 1px solid #e7e9f2;
        }
        .league-count {
            color: #8890a6;
            font-weight: 500;
            font-size: 0.85rem;
        }

        /* ---------- MATCH CARD ---------- */
        .match-card {
            background: #ffffff;
            border: 1px solid #e7e9f2;
            border-radius: 16px;
            padding: 16px 18px;
            margin-bottom: 14px;
            transition: box-shadow 0.15s ease, border 0.15s ease;
            box-shadow: 0 2px 10px rgba(30,40,80,0.04);
        }
        .match-card:hover {
            border: 1px solid #c9d3ff;
            box-shadow: 0 6px 20px rgba(60,90,220,0.10);
        }

        .match-top-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .match-hora {
            font-size: 0.78rem;
            color: #8890a6;
            font-weight: 600;
        }
        .match-teams {
            font-size: 1.02rem;
            font-weight: 700;
            color: #1b1f2e;
        }

        .pill {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 700;
            white-space: nowrap;
        }
        .pill-strategy {
            background: #eaf0ff;
            color: #3457d5;
            border: 1px solid #c9d3ff;
        }

        .prob-1x2 {
            display: flex;
            border-radius: 8px;
            overflow: hidden;
            height: 26px;
            margin: 8px 0 12px 0;
            font-size: 0.72rem;
            font-weight: 700;
            color: #ffffff;
        }
        .prob-seg {
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .stat-row {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }
        .stat-box {
            flex: 1;
            background: #f4f6fb;
            border-radius: 10px;
            padding: 8px 10px;
        }
        .stat-label {
            font-size: 0.66rem;
            color: #8890a6;
            text-transform: uppercase;
            letter-spacing: 0.4px;
            margin-bottom: 4px;
        }
        .stat-value {
            font-size: 0.9rem;
            font-weight: 700;
            color: #1b1f2e;
        }
        .bar-track {
            background: #e4e7f0;
            border-radius: 6px;
            height: 6px;
            margin-top: 6px;
            overflow: hidden;
        }
        .bar-fill { height: 100%; border-radius: 6px; }

        .extra-row {
            display: flex;
            gap: 16px;
            margin-top: 12px;
            font-size: 0.78rem;
            color: #5a6178;
        }
        .extra-item b { color: #1b1f2e; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def color_por_valor(v):
    if v >= 80:
        return "#1f9d55"  # verde
    if v >= 75:
        return "#b8860b"  # ámbar/dorado
    return "#3457d5"      # azul acento


# =============================================================================
# DATOS FICTICIOS (FASE 1 — cero consumo de API)
# =============================================================================
LIGAS_DEMO = [
    "ECUADOR - LIGA PRO",
    "ESPAÑA - LA LIGA",
    "INGLATERRA - PREMIER LEAGUE",
    "ARGENTINA - LIGA PROFESIONAL",
    "BRASIL - SERIE A",
    "ITALIA - SERIE A",
]

EQUIPOS_DEMO = [
    "Barcelona SC", "Emelec", "Liga de Quito", "Macará", "Aucas",
    "Real Madrid", "Barcelona", "Atlético Madrid", "Sevilla",
    "Manchester City", "Liverpool", "Arsenal", "Chelsea",
    "Boca Juniors", "River Plate", "Racing Club", "Independiente",
    "Flamengo", "Palmeiras", "Corinthians", "São Paulo",
    "Juventus", "Inter de Milán", "AC Milan", "Napoli",
]

ESTRATEGIAS_DEMO = [
    "Over 2.5 FT", "Over 1.5 FT", "Over 0.5 HT",
    "Gana Local (1)", "Ambos Anotan (AA)", "Gana / Empata Local",
]


def generar_partidos_ficticios(fecha, cantidad=18, semilla=None):
    """Genera un dataset ficticio con el mismo esquema que usará la data real,
    para poder pulir toda la interfaz sin tocar la API."""
    rng = random.Random(semilla or fecha)
    registros = []
    equipos_disponibles = EQUIPOS_DEMO.copy()

    for i in range(cantidad):
        liga = rng.choice(LIGAS_DEMO)
        rng.shuffle(equipos_disponibles)
        local, visita = equipos_disponibles[0], equipos_disponibles[1]

        hora = f"{rng.randint(11, 21):02d}:{rng.choice(['00', '15', '30', '45'])}"

        p_local = rng.randint(15, 65)
        p_empate = rng.randint(15, min(40, 100 - p_local - 5))
        p_visita = max(1, 100 - p_local - p_empate)

        p_05_ht = rng.randint(45, 92)
        p_15_ft = rng.randint(55, 96)
        p_25_ft = rng.randint(35, 90)
        p_aa = rng.randint(30, 88)

        prom_corners = round(rng.uniform(7.5, 13.2), 1)
        prom_tarjetas = round(rng.uniform(2.2, 7.2), 1)

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

        registros.append({
            "Liga": liga,
            "Hora (Ecuador)": hora,
            "Local": local,
            "Visita": visita,
            "Partido": f"{local} vs {visita}",
            "P. Local": p_local,
            "P. Empate": p_empate,
            "P. Visita": p_visita,
            "Estrategia Sugerida": estrategia,
            "+0.5 HT (%)": p_05_ht,
            "+1.5 FT (%)": p_15_ft,
            "+2.5 FT (%)": p_25_ft,
            "AA (%)": p_aa,
            "Prom. Córneres": prom_corners,
            "Prom. Tarjetas": prom_tarjetas,
        })

    return pd.DataFrame(registros).sort_values("Hora (Ecuador)").reset_index(drop=True)


# =============================================================================
# RENDER DE TARJETA DE PARTIDO
# =============================================================================
def render_tarjeta_partido(row):
    c_local = color_por_valor(row["P. Local"])
    c_empate = "#c3c8d6"
    c_visita = color_por_valor(row["P. Visita"])

    barras_html = ""
    for label, val in [
        ("+0.5 HT", row["+0.5 HT (%)"]),
        ("+1.5 FT", row["+1.5 FT (%)"]),
        ("+2.5 FT", row["+2.5 FT (%)"]),
        ("Ambos anotan", row["AA (%)"]),
    ]:
        color = color_por_valor(val)
        barras_html += f"""
        <div class="stat-box">
            <div class="stat-label">{label}</div>
            <div class="stat-value">{val}%</div>
            <div class="bar-track">
                <div class="bar-fill" style="width:{val}%; background:{color};"></div>
            </div>
        </div>
        """

    st.markdown(
        f"""
        <div class="match-card">
            <div class="match-top-row">
                <div>
                    <div class="match-hora">🕒 {row['Hora (Ecuador)']} (EC)</div>
                    <div class="match-teams">{row['Partido']}</div>
                </div>
                <span class="pill pill-strategy">🎯 {row['Estrategia Sugerida']}</span>
            </div>

            <div class="prob-1x2">
                <div class="prob-seg" style="width:{row['P. Local']}%; background:{c_local};">L {row['P. Local']}%</div>
                <div class="prob-seg" style="width:{row['P. Empate']}%; background:{c_empate}; color:#3d4358;">E {row['P. Empate']}%</div>
                <div class="prob-seg" style="width:{row['P. Visita']}%; background:{c_visita};">V {row['P. Visita']}%</div>
            </div>

            <div class="stat-row">
                {barras_html}
            </div>

            <div class="extra-row">
                <div class="extra-item">⛳ Córneres esperados: <b>{row['Prom. Córneres']}</b></div>
                <div class="extra-item">🟨 Tarjetas esperadas: <b>{row['Prom. Tarjetas']}</b></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# APP
# =============================================================================
inyectar_estilos()

st.markdown(
    f"""
    <div class="header-wrap">
        <p class="header-title">⚽ Tablero para Saladines, Donatelos y Donarumas</p>
        <p class="header-sub">Análisis dinámico individualizado por equipo y encuentro
        (Goles, Córneres y Tarjetas únicos por partido).</p>
        <span class="badge-modo">● MODO {'DATOS FICTICIOS — FASE DE DISEÑO' if MODO_DATOS == 'ficticio' else 'DATOS REALES'}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# SIDEBAR — FILTROS
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🎛️ Filtros")

    opcion_fecha = st.radio(
        "Fecha a consultar", ["Hoy", "Mañana"], horizontal=True
    )

    busqueda_equipo = st.text_input(
        "🔍 Buscar equipo", placeholder="Ej. Barcelona, Liga, Macará..."
    )

    filtro_probabilidad = st.selectbox(
        "🎯 Filtro de probabilidad",
        [
            "Todos los partidos",
            "Solo ≥ 75% en +0.5 HT",
            "Solo ≥ 80% en +0.5 HT",
            "Solo ≥ 80% en +1.5 FT",
            "Solo ≥ 75% en +2.5 FT",
        ],
    )

    ordenar_por = st.selectbox(
        "↕️ Ordenar por",
        ["Hora (Ecuador)", "+0.5 HT (%)", "+1.5 FT (%)", "+2.5 FT (%)", "AA (%)"],
    )

    st.markdown("---")
    st.caption(
        "Fase actual: **diseño con datos ficticios**. "
        "Cuando definamos el look final, conectamos el algoritmo real "
        "de estadísticas (API + fuente alterna) sin tocar esta interfaz."
    )
    recargar = st.button("🔄 Generar / refrescar partidos", use_container_width=True)

# ---------------------------------------------------------------------------
# CARGA DE DATOS
# ---------------------------------------------------------------------------
ahora_ec = datetime.now(TZ_ECUADOR)
fecha_consulta = (
    (ahora_ec + timedelta(days=1)).strftime("%Y-%m-%d")
    if opcion_fecha == "Mañana"
    else ahora_ec.strftime("%Y-%m-%d")
)

necesita_cargar = (
    "df_partidos" not in st.session_state
    or st.session_state.get("fecha_cargada") != fecha_consulta
    or recargar
)

if necesita_cargar:
    if MODO_DATOS == "ficticio":
        st.session_state["df_partidos"] = generar_partidos_ficticios(fecha_consulta)
    else:
        # FASE 2: aquí entra la carga real (API de fixtures/estadísticas
        # o la fuente alterna que evite consumir tokens de la API principal).
        st.session_state["df_partidos"] = generar_partidos_ficticios(fecha_consulta)
    st.session_state["fecha_cargada"] = fecha_consulta

df = st.session_state["df_partidos"].copy()

# ---------------------------------------------------------------------------
# APLICAR FILTROS
# ---------------------------------------------------------------------------
if busqueda_equipo:
    df = df[df["Partido"].str.contains(busqueda_equipo, case=False, na=False)]

if filtro_probabilidad == "Solo ≥ 75% en +0.5 HT":
    df = df[df["+0.5 HT (%)"] >= 75]
elif filtro_probabilidad == "Solo ≥ 80% en +0.5 HT":
    df = df[df["+0.5 HT (%)"] >= 80]
elif filtro_probabilidad == "Solo ≥ 80% en +1.5 FT":
    df = df[df["+1.5 FT (%)"] >= 80]
elif filtro_probabilidad == "Solo ≥ 75% en +2.5 FT":
    df = df[df["+2.5 FT (%)"] >= 75]

df = df.sort_values(
    by=ordenar_por, ascending=(ordenar_por == "Hora (Ecuador)")
)

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
k1, k2, k3, k4 = st.columns(4)
kpis = [
    (k1, len(df), "Partidos listados"),
    (k2, f"{df['+2.5 FT (%)'].mean():.0f}%" if len(df) else "—", "Prom. +2.5 FT"),
    (k3, f"{df['AA (%)'].mean():.0f}%" if len(df) else "—", "Prom. Ambos anotan"),
    (k4, f"{df['Prom. Córneres'].mean():.1f}" if len(df) else "—", "Prom. córneres/partido"),
]
for col, valor, label in kpis:
    with col:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-value">{valor}</div>
                <div class="kpi-label">{label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# LISTADO POR LIGA
# ---------------------------------------------------------------------------
if len(df) == 0:
    st.info("No se encontraron partidos con los filtros aplicados.")
else:
    for liga in df["Liga"].unique():
        df_liga = df[df["Liga"] == liga]
        st.markdown(
            f'<div class="league-title">🏆 {liga} '
            f'<span class="league-count">({len(df_liga)} partido/s)</span></div>',
            unsafe_allow_html=True,
        )

        cols = st.columns(2)
        for idx, (_, row) in enumerate(df_liga.iterrows()):
            with cols[idx % 2]:
                render_tarjeta_partido(row)
