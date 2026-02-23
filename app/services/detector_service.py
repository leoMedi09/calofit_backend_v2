"""
Detector de intención: comida vs ejercicio vs chat.
Usado para enrutar a nutricion_service o ejercicios_service y para respuestas rápidas.
"""
import re
from typing import Literal

TipoIntencion = Literal["comida", "ejercicio", "chat"]

KEYWORDS_COMIDA = [
    "calorias", "calorías", "caloria", "comida", "comí", "comer", "almuerzo", "cena", "desayuno",
    "receta", "plato", "alimento", "nutricion", "nutrición", "dieta", "macros", "proteina",
    "carbohidrato", "grasa", "registrar comida", "qué tiene", "cuantas calorias", "ají", "lomo",
    "arroz", "pollo", "pescado", "ensalada", "jugo", "torta", "pan", "huevo",
]
KEYWORDS_EJERCICIO = [
    "ejercicio", "rutina", "entrenamiento", "workout", "gimnasio", "correr", "caminar",
    "pesas", "flexiones", "sentadillas", "cardio", "quemar", "minutos de", "series", "repeticiones",
    "reps", "plancha", "burpees", "estiramiento",
]


def detectar_intencion(texto: str) -> TipoIntencion:
    """
    Detecta si el usuario pregunta por comida, ejercicio o chat general.
    """
    if not texto or not texto.strip():
        return "chat"
    t = texto.lower().strip()
    score_comida = sum(1 for k in KEYWORDS_COMIDA if k in t)
    score_ejercicio = sum(1 for k in KEYWORDS_EJERCICIO if k in t)
    if score_comida > score_ejercicio:
        return "comida"
    if score_ejercicio > score_comida:
        return "ejercicio"
    # Consultas directas tipo "cuántas calorías tiene X"
    if re.search(r"(cuántas|cuantas|qué tiene|que tiene|macros de)\s+\w+", t):
        return "comida"
    return "chat"
