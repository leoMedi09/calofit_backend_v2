import re
from datetime import datetime, date, timedelta, timezone
from typing import Optional, Dict

def get_peru_now() -> datetime:
    """Retorna la fecha y hora actual en zona horaria de Perú (UTC-5)"""
    # UTC now
    utc_now = datetime.now(timezone.utc)
    # Peru is UTC-5
    peru_time = utc_now - timedelta(hours=5)
    return peru_time

def get_peru_date() -> date:
    """Retorna la fecha actual en Perú"""
    return get_peru_now().date()


def parsear_macros_de_texto(macros_str: str) -> Optional[Dict[str, float]]:
    """
    Parsea string de macros tipo "P: 30g | C: 20g | G: 10g | Cal: 380kcal"
    a dict { proteinas_g, carbohidratos_g, grasas_g, calorias }.
    """
    if not macros_str or not macros_str.strip():
        return None
    s = macros_str.strip()
    # P / Proteína, C / Carbo, G / Grasa, Cal / Calorías
    p = re.search(r'P:\s*([\d.,]+)', s, re.IGNORECASE)
    c = re.search(r'C:\s*([\d.,]+)', s, re.IGNORECASE)
    g = re.search(r'G:\s*([\d.,]+)', s, re.IGNORECASE)
    cal = re.search(r'Cal:\s*([\d.,]+)', s, re.IGNORECASE)
    if not cal:  # alternativas
        cal = re.search(r'Calor[ií]as?:\s*([\d.,]+)', s, re.IGNORECASE)
    if not cal:
        cal = re.search(r'(\d+)\s*kcal', s, re.IGNORECASE)
    try:
        def to_float(m):
            if m is None:
                return 0.0
            return float(m.group(1).replace(',', '.'))
        return {
            "proteinas_g": to_float(p),
            "carbohidratos_g": to_float(c),
            "grasas_g": to_float(g),
            "calorias": to_float(cal),
        }
    except (ValueError, AttributeError):
        return None
