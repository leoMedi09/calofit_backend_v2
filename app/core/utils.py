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

def calcular_metabolismo_basal(cliente) -> float:
    """
    Calcula la Tasa Metabólica Basal usando la fórmula de Harris-Benedict revisada (Mifflin-St Jeor es otra opción, pero Harris-Benedict es la estándar en el proyecto).
    """
    from datetime import date
    # Calcular edad a partir de birth_date
    if cliente.birth_date:
        today = date.today()
        edad = today.year - cliente.birth_date.year - ((today.month, today.day) < (cliente.birth_date.month, cliente.birth_date.day))
    else:
        edad = 30  # Valor por defecto si no hay birth_date
    
    # Determinar género basado en el campo gender del cliente
    genero = getattr(cliente, 'gender', 'M')
    peso = cliente.weight or 75
    estatura = cliente.height or 170
    
    if genero == 'M':  # Masculino
        tmb = 88.362 + (13.397 * peso) + (4.799 * estatura) - (5.677 * edad)
    else:  # Femenino
        tmb = 447.593 + (9.247 * peso) + (3.098 * estatura) - (4.330 * edad)
    
    # Factor de actividad
    nivel_map = {
        "Sedentario": 1.20,
        "Ligero": 1.375,
        "Moderado": 1.55,
        "Activo": 1.725,
        "Muy activo": 1.90
    }
    factor = nivel_map.get(getattr(cliente, 'activity_level', 'Sedentario'), 1.20)
    return tmb * factor

def obtener_macros_desglosados(calorias: float, objetivo: str = "Mantener peso"):
    """
    Calcula desglose de macros basado en calorías y objetivo.
    Sincronizado con CalculadorDietaAutomatica (30/40/30).
    """
    # Ajustar según objetivo si es necesario (ya las calorías deberían venir ajustadas, 
    # pero aquí calculamos los gramos)
    pct_p, pct_c, pct_g = 0.30, 0.40, 0.30
    
    if objetivo == "Ganar masa":
        pct_p, pct_c, pct_g = 0.25, 0.50, 0.25
    elif objetivo == "Perder peso":
        pct_p, pct_c, pct_g = 0.35, 0.35, 0.30

    proteinas_g = (calorias * pct_p) / 4
    carbohidratos_g = (calorias * pct_c) / 4
    grasas_g = (calorias * pct_g) / 9
    
    return {
        "calorias": round(calorias),
        "proteinas_g": round(proteinas_g, 1),
        "carbohidratos_g": round(carbohidratos_g, 1),
        "grasas_g": round(grasas_g, 1),
        "pct": {
            "p": int(pct_p * 100),
            "c": int(pct_c * 100),
            "g": int(pct_g * 100)
        }
    }
