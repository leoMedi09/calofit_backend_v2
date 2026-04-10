"""Verificación post-limpieza de ia_service y ml_service."""
import sys
sys.path.insert(0, "/app")

from app.services.ia_service import ia_service, ia_engine
from app.services.ml_service import ml_perfil, ml_recomendador

print("OK ia_service y ia_engine cargados")
print(f"OK ml_perfil        | activo: {ml_perfil.modelo_activo}")
print(f"OK ml_recomendador  | activo: {ml_recomendador.modelo_activo}")

requeridos = [
    "calcular_requerimiento", "calcular_macros_completos", "calcular_macros_optimizados",
    "generar_alerta_fuzzy", "extraer_macros_de_texto", "identificar_intencion_salud",
    "interpretar_comando_nlp", "recomendar_alimentos_con_groq",
    "generar_sugerencia_entrenamiento", "generar_plan_inicial_automatico",
    "_llamar_groq",
]
eliminados = [
    "asistente_cliente", "calcular_tmb_mifflin", "generar_diagnostico_difuso",
    "recomendar_plan_nutricional", "consultar_fatsecret", "calcular_requerimiento_hibrido",
    # ml_service
]
ml_eliminados = ["get_descripcion", "recargar"]

print("\nMétodos obligatorios en ia_service:")
ok = True
for m in requeridos:
    existe = hasattr(ia_service, m)
    icono = "✅" if existe else "❌"
    print(f"  {icono} {m}")
    if not existe:
        ok = False

print("\nMétodos eliminados de ia_service:")
for m in eliminados:
    existe = hasattr(ia_service, m)
    icono = "✅ OK" if not existe else "❌ AUN EXISTE"
    print(f"  {icono} {m}")
    if existe:
        ok = False

print("\nMétodos eliminados de ml_service (ClasificadorPerfil):")
for m in ml_eliminados:
    existe = hasattr(ml_perfil, m)
    icono = "✅ OK" if not existe else "❌ AUN EXISTE"
    print(f"  {icono} {m}")
    if existe:
        ok = False

# Prueba funcional rápida
cal = ia_service.calcular_requerimiento(1, 25, 75, 175, 1.55, "mantener")
print(f"\nPrueba calcular_requerimiento: {cal} kcal")

alerta = ia_service.generar_alerta_fuzzy(70, 50)
print(f"Prueba generar_alerta_fuzzy:   {alerta['nivel']}")

intencion = ia_service.identificar_intencion_salud("Quiero comer arroz con pollo")
print(f"Prueba identificar_intencion:  {intencion}")

perfil, conf = ml_perfil.predecir_perfil_desde_progreso(registros_semana=4, adherencia_pct=70)
print(f"Prueba ml_perfil:              {perfil} ({conf}%)")

print()
print("RESULTADO:", "✅ TODO OK" if ok else "❌ HAY PROBLEMAS")
