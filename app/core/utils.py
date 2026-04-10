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
    Parsea string de macros en múltiples formatos que el LLM puede generar:
      - "P: 30g | C: 20g | G: 10g | Cal: 380kcal"
      - "653 kcal, 51g de proteína, 28g de grasa y 40g de carbohidratos"
      - "380 kcal | prot: 35g | carb: 45g | gras: 12g"
      - "Calorías: 500 | Proteínas: 40g | Carbohidratos: 50g | Grasas: 15g"
    """
    if not macros_str or not macros_str.strip():
        return None
    s = macros_str.strip()

    # ── Calorías ────────────────────────────────────────────────────
    cal = (
        re.search(r'Cal(?:or[ií]as?)?:\s*([\d.,]+)', s, re.IGNORECASE) or
        re.search(r'([\d.,]+)\s*kcal', s, re.IGNORECASE) or
        re.search(r'([\d.,]+)\s*cal\b', s, re.IGNORECASE)
    )

    # ── Proteínas ───────────────────────────────────────────────────
    p = (
        re.search(r'P(?:rot(?:eína?s?)?)?\s*:\s*([\d.,]+)', s, re.IGNORECASE) or
        re.search(r'([\d.,]+)\s*g\s*(?:de\s+)?prot(?:eína?s?)?', s, re.IGNORECASE) or
        re.search(r'prot(?:eína?s?)?\s*[:\-]\s*([\d.,]+)', s, re.IGNORECASE) or
        re.search(r'prot(?:eína?s?)?\s+([\d.,]+)\s*g', s, re.IGNORECASE)
    )

    # ── Carbohidratos ────────────────────────────────────────────────
    c = (
        re.search(r'C(?:arb(?:ohidrat[eo]s?)?)?\s*:\s*([\d.,]+)', s, re.IGNORECASE) or
        re.search(r'([\d.,]+)\s*g\s*(?:de\s+)?carb(?:ohidrat[eo]s?)?', s, re.IGNORECASE) or
        re.search(r'carb(?:ohidrat[eo]s?)?\s*[:\-]\s*([\d.,]+)', s, re.IGNORECASE) or
        re.search(r'carb(?:ohidrat[eo]s?)?\s+([\d.,]+)\s*g', s, re.IGNORECASE)
    )

    # ── Grasas ───────────────────────────────────────────────────────
    g = (
        re.search(r'G(?:ras(?:as?)?)?\s*:\s*([\d.,]+)', s, re.IGNORECASE) or
        re.search(r'([\d.,]+)\s*g\s*(?:de\s+)?gras(?:as?)?', s, re.IGNORECASE) or
        re.search(r'gras(?:as?)?\s*[:\-]\s*([\d.,]+)', s, re.IGNORECASE) or
        re.search(r'gras(?:as?)?\s+([\d.,]+)\s*g', s, re.IGNORECASE)
    )

    try:
        def to_float(m):
            if m is None:
                return 0.0
            return float(m.group(1).replace(',', '.'))

        cal_val  = to_float(cal)
        prot_val = to_float(p)
        carb_val = to_float(c)
        gras_val = to_float(g)

        # Si solo tenemos calorías, estimar macros proporcionales (30/40/30)
        if cal_val > 0 and prot_val == 0 and carb_val == 0 and gras_val == 0:
            prot_val = round(cal_val * 0.30 / 4, 1)
            carb_val = round(cal_val * 0.40 / 4, 1)
            gras_val = round(cal_val * 0.30 / 9, 1)

        if cal_val == 0 and prot_val == 0:
            return None

        return {
            "proteinas_g":    prot_val,
            "carbohidratos_g": carb_val,
            "grasas_g":       gras_val,
            "calorias":       cal_val,
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
    # Ajustar según objetivo
    obj_lower = objetivo.lower()
    pct_p, pct_c, pct_g = 0.30, 0.40, 0.30
    
    if "ganar" in obj_lower: # ganar masa o ganar_leve
        pct_p, pct_c, pct_g = 0.25, 0.50, 0.25
    elif "perder" in obj_lower: # perder peso o perder_leve
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
