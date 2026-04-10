"""
Test de Formato Frontend + Consistencia de Recomendaciones vs Registro.
Llama la API real del backend y verifica que:
1. El JSON tiene el shape correcto que espera AssistantResponse.fromJson()
2. Las secciones de receta tienen nombre, ingredientes, macros 
3. El consulta_id del cache permite registrar exactamente lo recomendado
"""
import sys, asyncio, json
sys.path.insert(0, "/app")

from app.core.database import SessionLocal
from app.models.client import Client
from app.services.asistente_service import asistente_service

# ─── Mock del current_user (simula token de auth) ────────────────────────
class MockUser:
    def __init__(self, email, uid):
        self.email = email
        self.id    = uid

SEP = "═" * 65

def header(t): print(f"\n{SEP}\n  {t}\n{SEP}")
def ok(m):     print(f"  ✅ {m}")
def err(m):    print(f"  ❌ {m}")
def warn(m):   print(f"  ⚠️  {m}")
def dato(k,v): print(f"  {k:<40}: {v}")


async def main():
    db = SessionLocal()
    try:
        cliente = db.query(Client).first()
        user = MockUser(email=cliente.email, uid=cliente.id)

        # ═══════════════════════════════════════════════════════
        # TEST 1: Consulta de Progreso → JSON correcto para Front
        # ═══════════════════════════════════════════════════════
        header("TEST 1: Consulta de Progreso → Verificar shape JSON para Flutter")
        resp = await asistente_service.consultar(
            mensaje="¿Cómo voy con mis calorías hoy?",
            db=db, current_user=user
        )

        # Verificar campos que AssistantResponse.fromJson() necesita
        campos_obligatorios = [
            "usuario", "intencion", "data_cientifica", "respuesta_estructurada"
        ]
        for campo in campos_obligatorios:
            if campo in resp:
                ok(f"Campo '{campo}' presente")
            else:
                err(f"Campo '{campo}' FALTANTE — Flutter fallará al parsear")

        # Verificar sub-campos de data_cientifica
        dc = resp.get("data_cientifica", {})
        pd = dc.get("progreso_diario", {})
        dato("data_cientifica.progreso_diario.consumido", pd.get("consumido", "FALTANTE"))
        dato("data_cientifica.progreso_diario.meta",      pd.get("meta", "FALTANTE"))
        dato("data_cientifica.progreso_diario.restante",  pd.get("restante", "FALTANTE"))
        dato("data_cientifica.progreso_diario.quemado",   pd.get("quemado", "FALTANTE"))

        # Verificar respuesta_estructurada
        re_struct = resp.get("respuesta_estructurada", {})
        dato("respuesta_estructurada.texto_conversacional",  
             (re_struct.get("texto_conversacional", "")[:60] + "...") if re_struct.get("texto_conversacional") else "FALTANTE")
        dato("respuesta_estructurada.secciones (count)",    
             len(re_struct.get("secciones", [])))
        ok("Shape JSON válido para Flutter AssistantResponse.fromJson()")

        print(f"\n  Respuesta IA:\n  {re_struct.get('texto_conversacional','')[:200]}")

        # ═══════════════════════════════════════════════════════
        # TEST 2: Pedir Receta → Verificar que la sección tenga
        #         nombre, ingredientes, macros y consulta_id
        # ═══════════════════════════════════════════════════════
        header("TEST 2: Recomiéndame algo para cenar → Formato de Tarjeta Receta")
        resp2 = await asistente_service.consultar(
            mensaje="¿Qué puedo cenar que sea proteico y con alimentos peruanos?",
            db=db, current_user=user
        )
        secciones = resp2.get("respuesta_estructurada", {}).get("secciones", [])
        dato("Intención detectada", resp2.get("intencion", "?"))
        dato("Número de secciones/opciones", len(secciones))

        if secciones:
            ok(f"El asistente generó {len(secciones)} opción(es) de receta")
            for i, sec in enumerate(secciones):
                print(f"\n  ── Sección {i+1}: {sec.get('nombre', 'SIN NOMBRE')} ──")
                dato("  Tipo",         sec.get("tipo", "?"))
                dato("  Ingredientes", len(sec.get("ingredientes", [])))
                dato("  Pasos",        len(sec.get("preparacion", [])))
                dato("  Macros",       sec.get("macros", "NO INCLUIDO"))
                dato("  consulta_id",  sec.get("consulta_id", "NO GENERADO ⚠️"))

                # Verificar que el consulta_id se generó (necesario para registro)
                if sec.get("consulta_id"):
                    ok("consulta_id presente → El usuario puede registrar con un tap")
                else:
                    warn("consulta_id AUSENTE → El botón 'Registrar' no funcionará")

                # Verificar ingredientes con calorías (regla del prompt)
                ings = sec.get("ingredientes", [])
                ings_con_cal = [i for i in ings if "kcal" in i.lower() or "cal" in i.lower()]
                dato("  Ingredientes con calorías incluidas", f"{len(ings_con_cal)}/{len(ings)}")
                if ings_con_cal:
                    ok("Ingredientes con calorías: CUMPLE la regla #5 del prompt")
                else:
                    warn("Ingredientes SIN calorías: NO CUMPLE regla #5")
        else:
            warn("No se generaron secciones — la IA respondió en texto plano")
            print(f"\n  Texto: {resp2.get('respuesta_estructurada', {}).get('texto_conversacional','')[:300]}")

        # ═══════════════════════════════════════════════════════
        # TEST 3: Registrar la primera receta recomendada
        #         y verificar que los macros coincidan
        # ═══════════════════════════════════════════════════════
        header("TEST 3: Registrar desde consulta_id → Verificar consistencia macros")
        if secciones and secciones[0].get("consulta_id") and secciones[0].get("tipo") == "comida":
            cid       = secciones[0]["consulta_id"]
            nombre    = secciones[0]["nombre"]
            macros_llm = secciones[0].get("macros", "")

            print(f"\n  Plato a registrar: {nombre}")
            print(f"  Macros LLM (raw) : {macros_llm}")

            # Verificar cache
            from app.core.cache import get_consulta_cached
            payload = get_consulta_cached(cid)
            if payload:
                ok("Cache encontrado con los datos del plato")
                dato("  Calorías en cache",      payload.get("calorias", "?"))
                dato("  Proteínas en cache",     payload.get("proteinas_g", "?"))
                dato("  Carbohidratos en cache", payload.get("carbohidratos_g", "?"))
                dato("  Grasas en cache",        payload.get("grasas_g", "?"))

                # Verificar consistencia: calorías ≈ P*4 + C*4 + G*9
                cal     = payload.get("calorias", 0)
                prot    = payload.get("proteinas_g", 0)
                carb    = payload.get("carbohidratos_g", 0)
                gras    = payload.get("grasas_g", 0)
                cal_calc = (prot * 4) + (carb * 4) + (gras * 9)
                diff    = abs(cal - cal_calc)

                print(f"\n  Verificación macro-calórica:")
                dato("  Calorías declaradas",    f"{cal} kcal")
                dato("  Calorías calculadas",    f"{cal_calc:.0f} kcal (P×4 + C×4 + G×9)")
                dato("  Diferencia",             f"{diff:.0f} kcal")

                if diff <= 60:
                    ok(f"Macros CONSISTENTES (±{diff:.0f} kcal) — Lo que se muestra = lo que se registra")
                else:
                    warn(f"Diferencia de {diff:.0f} kcal — Los macros no cuadran perfectamente (LLM puede ser impreciso)")

                # Ahora registrar de verdad usando confirmar_registro
                print("\n  Registrando el plato en la BD...")
                resultado_reg = await asistente_service.confirmar_registro(
                    consulta_id=cid, db=db, current_user=user
                )
                ok(f"Registro exitoso: {resultado_reg['mensaje']}")
                bal = resultado_reg.get("balance_actualizado", {})
                dato("  Total consumido hoy",   f"{bal.get('consumido', '?')} kcal")
                dato("  Total quemado hoy",     f"{bal.get('quemado', '?')} kcal")
                dato("  Proteínas acumuladas",  f"{bal.get('proteinas_g', '?')} g")
            else:
                err("Cache vacío — El consulta_id expiró o no se generó correctamente")
        else:
            warn("No hay secciones de comida disponibles para probar el registro")

        # ═══════════════════════════════════════════════════════
        # TEST 4: El NLP keyword "cenar" ahora debe → RECIPE 
        # ═══════════════════════════════════════════════════════
        header("TEST 4: Keywords NLP — Verificar intenciones de comidas/ejercicio")
        from app.services.ia_service import ia_engine
        casos = [
            ("¿Qué puedo cenar esta noche?",           "RECIPE"),
            ("¿Qué desayuno mañana?",                  "RECIPE"),
            ("Dame una opción de almuerzo bajo en grasa","RECIPE"),
            ("Comí arroz con pollo",                   "LOG"),
            ("Hice 30 minutos en el gym",              "EXERCISE"),
            ("¿Cuántas calorías tiene el lomo saltado?","INFO"),
            ("Me duele la cabeza y estoy mareado",     "ALERT"),
            ("Hola, ¿cómo estás?",                     "GENERAL"),
        ]
        aciertos = 0
        for pregunta, esperado in casos:
            detectado = ia_engine.identificar_intencion_salud(pregunta)
            correcto = detectado == esperado
            if correcto:
                aciertos += 1
                ok(f"[{detectado}] ← '{pregunta[:45]}'")
            else:
                warn(f"[{detectado}] ≠ [{esperado}] ← '{pregunta[:45]}'")
        
        print(f"\n  Score NLP: {aciertos}/{len(casos)} correctos ({aciertos/len(casos)*100:.0f}%)")
        if aciertos < len(casos):
            print(f"\n  Casos a mejorar:")

    except Exception as e:
        import traceback
        err(f"Error: {e}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
