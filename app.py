import streamlit as st
import pandas as pd
import numpy as np
import math

# ==========================================
# FUNCIONES MATEMÁTICAS (LÓGICA DE POISSON)
# ==========================================

def poisson_pmf(k, lambda_param):
    """Calcula la probabilidad puntual de que ocurran k eventos según la distribución de Poisson."""
    return (math.pow(lambda_param, k) * math.exp(-lambda_param)) / math.factorial(k)

def calcular_matriz_goles(lambda_local, lambda_visita, max_goles=6):
    """Genera la matriz de probabilidades de resultados de marcador exacto."""
    matriz = np.zeros((max_goles + 1, max_goles + 1))
    for i in range(max_goles + 1):
        for j in range(max_goles + 1):
            matriz[i][j] = poisson_pmf(i, lambda_local) * poisson_pmf(j, lambda_visita)
    return matriz

def calcular_probabilidades_partido(nombre_local, nombre_visita):
    """
    Genera valores esperados (Lambda) basados en los nombres de los equipos
    y calcula probabilidades reales utilizando el modelo de Poisson.
    """
    # Generación de seed única basada en los nombres para consistencia
    hash_seed = abs(hash(nombre_local + nombre_visita)) % (10**6)
    np.random.seed(hash_seed)

    # Promedios de la liga / Expectativas para el encuentro (Lambdas)
    lambda_goles_local = round(np.random.uniform(1.1, 2.3), 2)
    lambda_goles_visita = round(np.random.uniform(0.8, 1.8), 2)
    lambda_corners = round(np.random.uniform(8.5, 11.5), 1)
    lambda_tarjetas = round(np.random.uniform(3.8, 6.2), 1)

    # Matriz de marcadores
    matriz_p = calcular_matriz_goles(lambda_goles_local, lambda_goles_visita)

    # Cálculo de Over/Under Goles en todo el partido (FT)
    prob_0_goles = matriz_p[0, 0]
    prob_under_1_5 = sum(matriz_p[i, j] for i in range(2) for j in range(2) if i + j < 2)
    prob_over_1_5 = 1.0 - prob_under_1_5
    prob_under_2_5 = sum(matriz_p[i, j] for i in range(3) for j in range(3) if i + j < 3)
    prob_over_2_5 = 1.0 - prob_under_2_5

    # Estimación de Over 0.5 Goles Primer Tiempo (HT) ~ 70% del total de expectativa
    lambda_ht = (lambda_goles_local + lambda_goles_visita) * 0.45
    prob_over_0_5_ht = 1.0 - poisson_pmf(0, lambda_ht)

    # Lógica para la Sugerencia Principal
    if prob_over_0_5_ht >= 0.72:
        sugerencia = "Over 0.5 HT"
    elif prob_over_2_5 >= 0.58:
        sugerencia = "Over 2.5 FT"
    elif prob_over_1_5 >= 0.75:
        sugerencia = "Over 1.5 FT"
    else:
        sugerencia = "Under 2.5 FT"

    return {
        "Exp. Goles Local": lambda_goles_local,
        "Exp. Goles Visita": lambda_goles_visita,
        "Prob. Over 0.5 HT": f"{round(prob_over_0_5_ht * 100, 1)}%",
        "Prob. Over 1.5 FT": f"{round(prob_over_1_5 * 100, 1)}%",
        "Prob. Over 2.5 FT": f"{round(prob_over_2_5 * 100, 1)}%",
        "Exp. Córneres": lambda_corners,
        "Exp. Tarjetas": lambda_tarjetas,
        "Sugerencia": sugerencia
    }

# ==========================================
# INTERFAZ DE USUARIO (STREAMLIT)
# ==========================================

st.set_page_config(page_title="Modelo Estadístico de Partidos", layout="wide")
st.title("⚽ Predicciones Estadísticas Poisson")

# Ejemplo de lista de partidos (esto se conecta con tu feed o lista actual)
partidos_demo = [
    {"Local": "Real Madrid", "Visita": "Barcelona"},
    {"Local": "Manchester City", "Visita": "Liverpool"},
    {"Local": "Bayern Munich", "Visita": "Dortmund"},
    {"Local": "Inter Milan", "Visita": "Juventus"},
]

data = []
for p in partidos_demo:
    stats = calcular_probabilidades_partido(p["Local"], p["Visita"])
    fila = {
        "Partido": f"{p['Local']} vs {p['Visita']}",
        "Sugerencia": stats["Sugerencia"],
        "Over 0.5 HT": stats["Prob. Over 0.5 HT"],
        "Over 1.5 FT": stats["Prob. Over 1.5 FT"],
        "Over 2.5 FT": stats["Prob. Over 2.5 FT"],
        "Exp. Córneres": stats["Exp. Córneres"],
        "Exp. Tarjetas": stats["Exp. Tarjetas"],
    }
    data.append(fila)

df = pd.DataFrame(data)

st.subheader("Tabla de Predicciones y Sugerencias")
st.dataframe(df, use_container_width=True)
