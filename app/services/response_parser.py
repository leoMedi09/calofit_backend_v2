import re
from typing import Dict, List, Optional


def _sin_asteriscos(texto: str) -> str:
    """Elimina ** de Markdown para que Flutter no reciba negritas sin renderizar (evita overflow/visual)."""
    if not texto:
        return texto
    return re.sub(r"\*\*", "", str(texto))


def parsear_respuesta_para_frontend(texto_principal: str, mensaje_usuario: str = None) -> Dict:
    """
    Motor de parsing ultra-robusto (v11.0 - Protocolo Fallo Cero).
    Prioriza etiquetas blindadas [CALOFIT_XXX] y usa fallback elástico si no existen.
    """
    resultado = {
        "intent": "CHAT",
        "texto_conversacional": "",
        "secciones": [],
        "advertencia_nutricional": None
    }

    if not texto_principal: return resultado
    
    # --- PRE-PROCESAMIENTO: ESTANDARIZACIÓN DE ETIQUETAS (v15.0) ---
    # La IA a veces inyecta espacios: [/ CALOFIT_STATS] -> [/CALOFIT_STATS]
    # O usa minúsculas: [calofit_header] -> [CALOFIT_HEADER]
    def estandarizar_tags(texto: str) -> str:
        # Corregir cierres con espacios: [/ CALOFIT_XXX] -> [/CALOFIT_XXX]
        texto = re.sub(r'\[/\s*CALOFIT_([A-Z_]+)\s*\]', r'[/CALOFIT_\1]', texto, flags=re.IGNORECASE)
        # Corregir aperturas con espacios: [ CALOFIT_XXX ] -> [CALOFIT_XXX]
        texto = re.sub(r'\[\s*CALOFIT_([A-Z_]+)(?::\s*.*?)?\s*\]', lambda m: m.group(0).replace(" ", ""), texto, flags=re.IGNORECASE)
        # Forzar mayúsculas en tags conocidos
        tags_validos = ["CHAT", "ITEM_RECIPE", "ITEM_WORKOUT", "HEADER", "STATS", "LIST", "ACTION", "FOOTER", "INTENT"]
        for tag in tags_validos:
            texto = re.sub(fr'\[/?CALOFIT_{tag}', f'[{tag_part}' if (tag_part := re.search(fr'\[/?CALOFIT_{tag}', texto, re.I)) and tag_part.group().startswith('[/') else f'[CALOFIT_{tag}', texto, flags=re.IGNORECASE)
        return texto

    # v15.1: Regex más simple para estandarizar tags sin romper intents
    texto_principal = re.sub(r'\[\s*(/?CALOFIT_[A-Z_]+)(?:\s*:\s*([A-Z_]+))?\s*\]', 
                             lambda m: f"[{m.group(1).upper().strip()}{': ' + m.group(2).upper().strip() if m.group(2) else ''}]", 
                             texto_principal, flags=re.IGNORECASE)
    # Corregir espacios en cierres residuales
    texto_principal = re.sub(r'\[/\s*(CALOFIT_[A-Z_]+)\s*\]', r'[/\1]', texto_principal, flags=re.IGNORECASE)
    
    # 🛡️ FIX v73.0: Eliminar etiquetas de cierre huérfanas o mal formadas al inicio de la respuesta
    texto_principal = re.sub(r'^\[/CALOFIT_[A-Z_]+\]\s*', '', texto_principal, flags=re.IGNORECASE)
    intent_match = re.search(r'\[CALOFIT_INTENT:\s*(\w+)\]', texto_principal, re.IGNORECASE)
    if intent_match:
        resultado["intent"] = intent_match.group(1).upper()
        # Limpiar la etiqueta del texto para no mostrarla al usuario
        texto_principal = texto_principal.replace(intent_match.group(0), "").strip()

    # --- FASE 2: EXTRACCIÓN POR ETIQUETAS BLINDADAS (PROTOCOLO 3.5 - MULTI-SECCIÓN) ---
    # Detectar headers sin importar mayúsculas/minúsculas
    if re.search(r'\[CALOFIT_HEADER\]', texto_principal, re.IGNORECASE):
        # Dividir el texto en potenciales bloques de sección (cada bloque empieza con intent o header)
        bloques_raw = re.split(r'(\[CALOFIT_INTENT:.*?\]|\[CALOFIT_HEADER\])', texto_principal, flags=re.IGNORECASE)
        
        # Reconstruir bloques lógicos
        bloques_reales = []
        i = 1 
        while i < len(bloques_raw):
            etiqueta = bloques_raw[i]
            contenido = bloques_raw[i+1] if (i+1) < len(bloques_raw) else ""
            bloques_reales.append(etiqueta + contenido)
            i += 2

        for bloque in bloques_reales:
            header = re.search(r'\[CALOFIT_HEADER\](.*?)\[/CALOFIT_HEADER\]', bloque, re.DOTALL | re.IGNORECASE)
            stats = re.search(r'\[CALOFIT_STATS\](.*?)\[/CALOFIT_STATS\]', bloque, re.DOTALL | re.IGNORECASE)
            lista = re.search(r'\[CALOFIT_LIST\](.*?)\[/CALOFIT_LIST\]', bloque, re.DOTALL | re.IGNORECASE)
            action = re.search(r'\[CALOFIT_ACTION\](.*?)\[/CALOFIT_ACTION\]', bloque, re.DOTALL | re.IGNORECASE)
            footer = re.search(r'\[CALOFIT_FOOTER\](.*?)\[/CALOFIT_FOOTER\]', bloque, re.DOTALL | re.IGNORECASE)

            if header or lista:
                # 🎯 DETECCIÓN DE TIPO MEJORADA (v12.1 - INTENT POR BLOQUE + DEBUG MACROS)
                bloque_low = bloque.lower()
                tipo = "comida"  # Default

                # 1. Prioridad: Intent dentro del propio bloque (multi-opcion tiene un intent por bloque)
                bloque_intent_match = re.search(r'\[CALOFIT_INTENT:\s*(\w+)\]', bloque, re.IGNORECASE)
                bloque_intent = bloque_intent_match.group(1).upper() if bloque_intent_match else resultado["intent"]

                if bloque_intent in ["ITEM_WORKOUT", "WORKOUT", "EXERCISE"]:
                    tipo = "ejercicio"
                elif bloque_intent in ["ITEM_RECIPE", "RECIPE", "FOOD", "MEAL"]:
                    tipo = "comida"
                else:
                    # 2. Fallback: Keywords en el bloque
                    kw_ejercicio = ["series", "repeticiones", "reps", "sets", "plancha", "sentadillas",
                                    "flexiones", "abdominales", "cardio", "calentamiento", "rutina",
                                    "workout", "ejercicio", "burpees", "trote"]
                    kw_comida = ["ingredientes", "preparación", "preparacion", "cocina", "gramos", "cucharada",
                                 "recipe", "comida", "plato", "receta"]

                    ejercicio_score = sum(1 for kw in kw_ejercicio if kw in bloque_low)
                    comida_score = sum(1 for kw in kw_comida if kw in bloque_low)

                    if ejercicio_score > comida_score:
                        tipo = "ejercicio"
                    elif comida_score > 0:
                        tipo = "comida"
                
                # Limpiar items - Regex mejorado (v63): No borrar (X kcal)
                if lista:
                    items_raw = lista.group(1).strip().split('\n')
                else:
                    items_raw = re.findall(r'^\s*[-\*•]\s+(.+)$', bloque, re.MULTILINE)

                # v63: Solo borra bullets, NO borra el contenido entre paréntesis si parece kcal
                items = []
                for i in items_raw:
                    linea = i.strip()
                    if not linea: continue
                    # Limpiar bullet inicial
                    linea = re.sub(r'^(\s*[-\*•]\s?|\s*\d+[\.\)]\s?)', '', linea).strip()
                    # Filtrar encabezados de lista
                    if re.match(r'^(ingredientes|ejercicios|lista)[:\.]?$', linea, re.IGNORECASE): continue
                    items.append(linea)

                # Limpiar pasos
                if action:
                    pasos_raw = action.group(1).strip().split('\n')
                else:
                    # Fallback: Buscar líneas numeradas (1., 2.)
                    pasos_raw = re.findall(r'^\s*\d+[\.\)]\s+(.+)$', bloque, re.MULTILINE)
                    
                # Igual para pasos, manteniendo el texto limpio
                pasos = [re.sub(r'^(\s*[-\*•]\s?|\s*\d+[\.\)]\s?)', '', p).strip() for p in pasos_raw if p.strip()]
                
                # 🚀 HEURÍSTICA DE SEGURIDAD (v72.0): Detectar pasos mezclados en ingredientes
                # Si un ingrediente empieza con verbos de acción, moverlo a pasos
                verbos_accion = ["sirve", "disfruta", "lleva", "cocina", "mezcla", "hornea", "calienta", "pica", "corta", "agrega", "añade"]
                ingredientes_originales = items[:]
                items = []
                for ing in ingredientes_originales:
                    ing_low = ing.lower()
                    if any(ing_low.startswith(v) for v in verbos_accion) and len(ing) > 10:
                        pasos.append(ing)
                    else:
                        items.append(ing)

                # Filtrar líneas que solo digan "preparación:" o similar
                pasos = [p for p in pasos if not re.match(r'^(preparaci[oó]n|instrucciones|pasos|tecnica)[:\.]?$', p, re.IGNORECASE)]

                msg_stats = stats.group(1).strip() if stats else ""
                # v64: Normalizar formato de macros para que el RecipeCard lo entienda perfectamente
                # Eliminar emojis o texto extra que confunda al parseador de chips del frontend
                msg_stats_clean = msg_stats.replace('💪', '').replace('🌾', '').replace('🥑', '').replace('🔥', '').strip()
                # Asegurar formato P: X | C: Y | G: Z | Cal: W
                msg_stats_clean = re.sub(r'\(Ajustado.*?\)', '', msg_stats_clean).strip()
                
                # Si el backend inyectó algo como "P: 30g, C: 20g" corregir a "|"
                # v65.8: Solo reemplazar coma si va seguida de espacio y parece un nuevo macro (Proteína, Carbo, etc)
                msg_stats_clean = re.sub(r',\s*(?=(?:P|C|G|Cal|Prot|Gras|Carb)\b)', ' | ', msg_stats_clean, flags=re.IGNORECASE)

                # v65: Normalizar nombres de macros de largo a corto para el frontend
                msg_stats_clean = re.sub(r'Prote\w*', 'P', msg_stats_clean, flags=re.IGNORECASE)
                msg_stats_clean = re.sub(r'Carbo\w*', 'C', msg_stats_clean, flags=re.IGNORECASE)
                msg_stats_clean = re.sub(r'Grasa\w*', 'G', msg_stats_clean, flags=re.IGNORECASE)
                msg_stats_clean = re.sub(r'Calor\w*', 'Cal', msg_stats_clean, flags=re.IGNORECASE)

                nombre_raw = header.group(1).strip() if header else "Sugerencia CaloFit"
                nombre_clean = re.sub(r'^(Opci[oó]n|Option|Plato|Platillo|Rutina|Receta)\s*\d+[:\.]?\s*', '', nombre_raw, flags=re.IGNORECASE).strip()
                # Flutter: sin ** para evitar asteriscos sin renderizar
                nombre_clean = _sin_asteriscos(nombre_clean)
                items_clean = [_sin_asteriscos(i) for i in items]
                pasos_clean = [_sin_asteriscos(p) for p in pasos]
                msg_stats_clean = _sin_asteriscos(msg_stats_clean)

                seccion = {
                    "tipo": tipo,
                    "nombre": nombre_clean,
                    "justificacion": "",
                    "ingredientes": items_clean if tipo == "comida" else [],
                    "ejercicios": items_clean if tipo == "ejercicio" else [],
                    "preparacion": pasos_clean if tipo == "comida" else [],
                    "tecnica": pasos_clean if tipo == "ejercicio" else [],
                    "instrucciones": pasos_clean if tipo == "ejercicio" else [],
                    "macros": msg_stats_clean,
                    "gasto_calorico_estimado": msg_stats_clean if tipo == "ejercicio" else "",
                    "nota": footer.group(1).strip() if footer else ""
                }
                
                # 🛡️ LIMPIEZA QUIRÚRGICA DE CAMPOS (v73.1): Eliminar tags que se colaron en los valores
                for campo in ["nombre", "macros", "gasto_calorico_estimado", "nota"]:
                    val = seccion.get(campo, "")
                    if isinstance(val, str):
                        seccion[campo] = re.sub(r'\[/?CALOFIT_[A-Z_]+.*?\]', '', val, flags=re.IGNORECASE).strip()
                
                for lista_campo in ["ingredientes", "ejercicios", "preparacion", "tecnica", "instrucciones"]:
                    lista_val = seccion.get(lista_campo, [])
                    if isinstance(lista_val, list):
                        seccion[lista_campo] = [re.sub(r'\[/?CALOFIT_[A-Z_]+.*?\]', '', item, flags=re.IGNORECASE).strip() for item in lista_val if item.strip()]
                
                # De-duplicación y guardado
                if not any(s["nombre"] == seccion["nombre"] for s in resultado["secciones"]):
                    resultado["secciones"].append(seccion)

        # --- FASE 3: RECONSTRUCCIÓN DE COMPVERSACIÓN (SIN RESIDUOS DE RECETAS) ---
        # Estrategia: "Split and Select". Solo mantenemos texto que NO pertenece a un bloque HEADER.
        # bloques_raw[0] es el texto antes del primer tag.
        # bloques_raw[1], [3]... son los tags.
        # bloques_raw[2], [4]... son los contenidos.
        
        texto_limpio_parts = [bloques_raw[0]]
        k = 1
        while k < len(bloques_raw):
            tag = bloques_raw[k]
            content = bloques_raw[k+1] if (k+1) < len(bloques_raw) else ""
            
            # 🛡️ FIX v72.1: Solo meter al chat el contenido de [CALOFIT_INTENT: CHAT]
            # Ignorar ITEM_RECIPE, ITEM_WORKOUT y tags de HEADER, ya que van a Cards.
            if "[CALOFIT_INTENT: CHAT]" in tag.upper():
                texto_limpio_parts.append(content)
            elif "[CALOFIT_INTENT" not in tag.upper() and "[CALOFIT_HEADER]" not in tag.upper():
                # Si es un bloque de texto que quedó fuera de los tags por error de la IA, lo incluimos
                # pero limpiamos cualquier tag residual
                texto_sucio = re.sub(r'\[/?CALOFIT_[A-Z_]+.*?\]', '', content, flags=re.IGNORECASE)
                texto_limpio_parts.append(texto_sucio)
            
            k += 2
            
        texto_limpio = "".join(texto_limpio_parts)
        
        # --- FASE 4: FORMATEO VISUAL (LISTAS BONITAS) ---
        # Detectar listas pegadas (ej: "incluyen: * Tofu") y forzar saltos de línea
        # Regex: Espacio/Punto + [bullet/numero] + espacio -> Newline + bullet
        texto_limpio = re.sub(r'([:;.])\s*([-\*•]|\d+\.)\s+', r'\1\n\2 ', texto_limpio) # Case: "text: * Item" -> "text:\n* Item"
        texto_limpio = re.sub(r'\s+([-\*•])\s+', r'\n\1 ', texto_limpio) # Case: "Item 1 * Item 2" -> "Item 1\n* Item 2"
        # Evitar romper numeros en medio de texto, solo si parece una lista (num + punto)
        texto_limpio = re.sub(r'\s+(\d+\.)\s+', r'\n\1 ', texto_limpio) 

        # Eliminar etiquetas residuales o cabeceras alucinadas (ej: "**CHAT**", "**ITEM_RECIPE**")
        texto_limpio = re.sub(r'^\s*\*\*?(CHAT|ITEM_RECIPE|ITEM_WORKOUT|ASISTENTE|RESPUESTA|INTENT|PLAN_DIET|PLAN_WORKOUT)\*\*?\s*', '', texto_limpio, flags=re.IGNORECASE)
        
        # 🧹 LIMPIEZA FINAL: Eliminar nombres de platos/ejercicios que quedaron en texto plano
        # Si detectamos los nombres de las secciones en el texto conversacional, los borramos
        for seccion in resultado["secciones"]:
            nombre_plato = seccion["nombre"]
            # Eliminar el nombre si aparece literal en el texto (suele estar en mayúsculas o con formato)
            # Casos: "TACACHO DE HUEVOS", "Tacacho de Huevos", etc.
            texto_limpio = re.sub(r'\b' + re.escape(nombre_plato) + r'\b', '', texto_limpio, flags=re.IGNORECASE)
            # También eliminar versiones en mayúsculas completas
            texto_limpio = re.sub(r'\b' + re.escape(nombre_plato.upper()) + r'\b', '', texto_limpio)
        
        # Limpiar espacios múltiples y saltos de línea excesivos generados por las eliminaciones
        texto_limpio = re.sub(r'\n\s*\n\s*\n+', '\n\n', texto_limpio)
        texto_limpio = re.sub(r'  +', ' ', texto_limpio)
        
        # Flutter: eliminar
        # 🛡️ LIMPIEZA FINAL DE CUALQUIER TAG RESIDUAl [/CALOFIT_...]
        texto_limpio = re.sub(r'\[/?CALOFIT_[A-Z_]+.*?\]', '', texto_limpio, flags=re.IGNORECASE)
        resultado["texto_conversacional"] = _sin_asteriscos(texto_limpio.strip())
        return resultado

    # --- FASE 3: FALLBACK A PARSER ELÁSTICO (Formato Antiguo) ---
    # v71.1: Mejorado para detectar patrones naturales como "Opción 1: Sopa de Lentejas"
    t = texto_principal.replace('***', '').strip()
    lineas = [l.strip() for l in t.split('\n') if l.strip()]
    
    # Patrones de inicio de sección EXPANDIDOS para detectar formato natural de la IA
    # Detecta: "plato: X", "Opción 1: X", "**Opción 1: X**", "1. X", "Receta 1: X"
    opcion_pattern = re.compile(
        r'^(?:\*{0,2})?(?:Opci[oó]n|Receta|Rutina|Plato|Opcion|Ejercicio)\s*\d*[:\.\)]\s*(.+?)(?:\*{0,2})?$',
        re.IGNORECASE
    )
    # También detectar líneas en negritas que son títulos cortos (posibles nombres de platos)
    titulo_bold_pattern = re.compile(r'^\*\*(.{5,60})\*\*$')
    
    old_start_markers = ["plato:", "rutina:", "receta:", "nombre:", "ejercicio:", "comida:"]
    
    current_section = None
    last_key = None
    intro_lines = []

    for l in lineas:
        l_low = l.lower()
        l_clean = re.sub(r'\*\*', '', l).strip()
        
        # Detectar inicio de sección: marcadores clásicos O "Opción N:"
        is_classic_start = any(l_low.startswith(m) for m in old_start_markers)
        opcion_match = opcion_pattern.match(l_clean)
        titulo_bold_match = titulo_bold_pattern.match(l) if not current_section else None
        
        # Decidir inicio según match
        new_section_nombre = None
        new_section_tipo = "comida"
        
        if is_classic_start:
            new_section_nombre = l.split(':', 1)[1].strip() if ':' in l else l_clean
            new_section_tipo = "ejercicio" if "rutina" in l_low or "ejercicio" in l_low else "comida"
        elif opcion_match:
            new_section_nombre = opcion_match.group(1).strip().strip('*').strip()
            new_section_tipo = "ejercicio" if any(k in l_low for k in ["rutina", "ejercicio", "entrenamiento"]) else "comida"
        
        if new_section_nombre:
            if current_section and current_section.get("ingredientes"):
                resultado["secciones"].append(current_section)
            current_section = {
                "tipo": new_section_tipo, 
                "nombre": _sin_asteriscos(new_section_nombre), 
                "justificacion": "", 
                "ingredientes": [], 
                "preparacion": [], 
                "macros": "", 
                "nota": ""
            }
            last_key = "nombre"
            # Esta línea es un header, va al texto conversacional NO a la card
            # (solo si hay secciones ya o es una opción múltiple)
            continue

        if not current_section:
            # AUTO-RESCATE (v71.6): Si la IA saltó directamente a los ingredientes (bullet points) sin poner un título
            if re.match(r'^[-\*•]\s+', l) and ('g' in l_low or 'cda' in l_low or 'taza' in l_low):
                current_section = {
                    "tipo": "comida", 
                    "nombre": f"Sugerencia {len(resultado['secciones']) + 1}", 
                    "justificacion": "", 
                    "ingredientes": [], 
                    "preparacion": [], 
                    "macros": "", 
                    "nota": ""
                }
                # Seguimos procesando esta línea como si fuera un ingrediente
            elif re.match(r'^\d+[\.\)]\s+', l) and ('precalienta' in l_low or 'mezcla' in l_low or 'hornea' in l_low):
                 current_section = {
                    "tipo": "comida", 
                    "nombre": f"Sugerencia {len(resultado['secciones']) + 1}", 
                    "justificacion": "", 
                    "ingredientes": [], 
                    "preparacion": [], 
                    "macros": "", 
                    "nota": ""
                }
            else:
                intro_lines.append(l)
                continue

        # Procesar campos dentro de sección
        if "ingredientes" in l_low or "componentes" in l_low: 
            last_key = "ingredientes"
        elif "preparaci" in l_low or "elaboraci" in l_low or "c\u00f3mo preparar" in l_low or "pasos" in l_low:
            last_key = "preparacion"
        elif "macros" in l_low or "aporte" in l_low or "calorias" in l_low or "kcal" in l_low.replace(' ', '') and ':' in l_low:
            last_key = "macros"
            if ':' in l:
                current_section["macros"] = l.split(':', 1)[1].strip()
        elif "nota" in l_low or "recuerda" in l_low: 
            last_key = "nota"
        else:
            if last_key in ["ingredientes", "preparacion"]:
                item = re.sub(r'^([-\*\+\#•]|\d+[\.#\)\s])\s*', '', l_clean).strip()
                if item and not re.match(r'^(ingredientes|ejercicios|preparaci[oó]n|lista)[:\.]?$', item, re.IGNORECASE):
                    current_section[last_key].append(_sin_asteriscos(item))
            elif last_key == "macros":
                current_section["macros"] = (current_section["macros"] + " " + l_clean).strip()
            elif last_key:
                current_section[last_key] = (current_section.get(last_key, "") + " " + l_clean).strip()
            # Auto-detectar ingredientes si la línea empieza por bullet y estamos en sección de comida
            elif re.match(r'^[-\*•]\s+', l) and current_section["tipo"] == "comida":
                item = re.sub(r'^[-\*•]\s+', '', l).strip()
                if item:
                    current_section["ingredientes"].append(_sin_asteriscos(item))
                    last_key = "ingredientes"
            # Auto-detectar pasos si empieza por número
            elif re.match(r'^\d+[\.\)]\s+', l):
                item = re.sub(r'^\d+[\.\)]\s+', '', l).strip()
                if item:
                    current_section["preparacion"].append(_sin_asteriscos(item))
                    last_key = "preparacion"

    if current_section and current_section.get("ingredientes"):
        if current_section["tipo"] == "ejercicio":
            current_section["ejercicios"] = current_section.pop("ingredientes")
            current_section["tecnica"] = current_section.pop("preparacion")
            current_section["gasto_calorico_estimado"] = current_section.pop("macros")
        resultado["secciones"].append(current_section)

    # El texto conversacional solo tiene las líneas de introducción
    texto_limpio = "\n".join(intro_lines).strip()
    
    # FASE 4: Formateo visual
    texto_limpio = re.sub(r'([:;.])\s*([-\*•]|\d+\.)\s+', r'\1\n\2 ', texto_limpio)
    texto_limpio = re.sub(r'\s+([-\*•])\s+', r'\n\1 ', texto_limpio)
    texto_limpio = re.sub(r'\s+(\d+\.)\s+', r'\n\1 ', texto_limpio) 
    
    resultado["texto_conversacional"] = texto_limpio
    return resultado
