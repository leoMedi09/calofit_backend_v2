"""
Sustituciones por restricción dietética (vegano, vegetariano, etc.).
Si el usuario pide un plato que no cumple su restricción, ofrecer alternativa.
"""
from typing import List, Optional, Tuple

# Mapa: (restricción, alimento_origen) -> lista de sustitutos
SUSTITUCIONES: List[Tuple[str, str, List[str]]] = [
    ("vegano", "ají de gallina", ["ají de setas", "ají de tofu", "ají de chocho"]),
    ("vegano", "lomo saltado", ["saltado de seitán", "saltado de tofu", "saltado de champiñones"]),
    ("vegano", "arroz con pato", ["arroz con seitán", "arroz con tofu", "arroz con legumbres"]),
    ("vegano", "pollo", ["tofu", "seitán", "garbanzos", "lentejas"]),
    ("vegano", "carne", ["tofu", "seitán", "lentejas", "champiñones"]),
    ("vegano", "pescado", ["tofu", "alga nori", "champiñones"]),
    ("vegano", "huevo", ["tofu revuelto", "garbanzo molido", "linaza"]),
    ("vegano", "leche", ["leche de soja", "leche de avena", "leche de almendras"]),
    ("vegetariano", "pollo", ["tofu", "huevo", "queso"]),
    ("vegetariano", "carne", ["tofu", "huevo", "legumbres"]),
]


def normalizar_restriccion(restriccion: str) -> str:
    if not restriccion:
        return ""
    r = restriccion.lower().strip()
    if "vegan" in r:
        return "vegano"
    if "vegetar" in r:
        return "vegetariano"
    return r


def buscar_sustitutos(restriccion: str, nombre_plato_o_alimento: str) -> Optional[List[str]]:
    """
    Si el usuario tiene restricción y pide algo que no cumple, devuelve lista de sustitutos.
    nombre_plato_o_alimento: ej. "ají de gallina", "pollo".
    """
    r = normalizar_restriccion(restriccion)
    if not r:
        return None
    nombre = nombre_plato_o_alimento.lower().strip()
    for rest, origen, sustitutos in SUSTITUCIONES:
        if rest == r and (origen in nombre or nombre in origen):
            return sustitutos
    return None


def tiene_restriccion(contexto_perfil: str) -> bool:
    """Indica si en el contexto del perfil hay restricción vegana/vegetariana."""
    c = (contexto_perfil or "").lower()
    return "vegano" in c or "vegetariano" in c or "vegetariana" in c
