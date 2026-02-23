"""
Calculador de requerimientos nutricionales con Mifflin-St Jeor.
TMB = tasa metabólica basal; GET = gasto energético total.
Personalizado por usuario (edad, peso, talla, género, nivel actividad, objetivo).
"""
from typing import Dict

# Factores de actividad (GET = TMB * factor)
FACTORES_ACTIVIDAD = {
    "Sedentario": 1.20,
    "Ligero": 1.375,
    "Moderado": 1.55,
    "Activo": 1.725,
    "Muy activo": 1.90,
}

# Ajuste calórico por objetivo (kcal/día)
AJUSTE_OBJETIVO = {
    "perder_agresivo": -500,
    "perder_definicion": -300,
    "mantener": 0,
    "ganar_lean_bulk": 250,
    "ganar_bulk": 500,
    "perder": -500,
    "ganar": 500,
}


def tmb_mifflin_st_jeor(genero: str, edad: int, peso_kg: float, talla_cm: float) -> float:
    """
    Tasa metabólica basal (Mifflin-St Jeor).
    genero: 'M' o 'F'
    edad: años; peso_kg: kg; talla_cm: cm.
    """
    if genero and str(genero).upper() == "F":
        return 10 * peso_kg + 6.25 * talla_cm - 5 * edad - 161
    return 10 * peso_kg + 6.25 * talla_cm - 5 * edad + 5


def get_diario(tmb: float, nivel_actividad: str) -> float:
    """Gasto energético total = TMB * factor de actividad."""
    factor = FACTORES_ACTIVIDAD.get(nivel_actividad, 1.20)
    return tmb * factor


def calorias_objetivo(get_val: float, objetivo_key: str) -> float:
    """Calorías objetivo = GET + ajuste por objetivo."""
    ajuste = AJUSTE_OBJETIVO.get(objetivo_key.lower() if objetivo_key else "mantener", 0)
    return max(1200, get_val + ajuste)


def macros_por_objetivo(
    peso_kg: float,
    objetivo_key: str,
    calorias_diarias: float,
    condiciones_medicas: str = "",
) -> Dict[str, float]:
    """
    Calcula P, C, G en gramos (misma lógica que ia_service.calcular_macros_optimizados).
    Retorna proteinas_g, carbohidratos_g, grasas_g; opcional alerta_medica.
    """
    condiciones = (condiciones_medicas or "").lower()
    if "perder" in (objetivo_key or "").lower():
        g_proteina_kg = 2.2
        g_grasa_kg = 0.7
    elif "ganar" in (objetivo_key or "").lower():
        g_proteina_kg = 1.8
        g_grasa_kg = 1.0
    else:
        g_proteina_kg = 2.0
        g_grasa_kg = 0.9

    proteinas_g = round(peso_kg * g_proteina_kg, 1)
    grasas_g = round(peso_kg * g_grasa_kg, 1)
    calorias_p_g = proteinas_g * 4 + grasas_g * 9
    calorias_restantes = max(0, calorias_diarias - calorias_p_g)
    carbohidratos_g = round(calorias_restantes / 4, 1)

    if "diabetes" in condiciones or "resistencia a la insulina" in condiciones:
        limite_carbos = peso_kg * 3
        if carbohidratos_g > limite_carbos:
            carbohidratos_g = round(limite_carbos, 1)

    return {
        "proteinas_g": proteinas_g,
        "carbohidratos_g": carbohidratos_g,
        "grasas_g": grasas_g,
    }


def calcular_todo(
    genero: str,
    edad: int,
    peso_kg: float,
    talla_cm: float,
    nivel_actividad: str = "Moderado",
    objetivo: str = "mantener",
    condiciones_medicas: str = "",
) -> Dict:
    """
    Retorna dict con tmb, get, calorias_objetivo, proteinas_g, carbohidratos_g, grasas_g.
    """
    tmb = tmb_mifflin_st_jeor(genero, edad, peso_kg, talla_cm)
    get_val = get_diario(tmb, nivel_actividad)
    cal_obj = calorias_objetivo(get_val, objetivo)
    macros = macros_por_objetivo(peso_kg, objetivo, cal_obj, condiciones_medicas)
    return {
        "tmb": round(tmb, 2),
        "get": round(get_val, 2),
        "calorias_objetivo": round(cal_obj, 2),
        "proteinas_g": macros["proteinas_g"],
        "carbohidratos_g": macros["carbohidratos_g"],
        "grasas_g": macros["grasas_g"],
    }
