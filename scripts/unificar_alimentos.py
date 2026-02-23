
import json
import os
import unicodedata

def normalizar_texto(texto):
    if not texto: return ""
    # Remover tildes y convertir a lowercase
    texto = unicodedata.normalize('NFD', texto)
    texto = "".join([c for c in texto if unicodedata.category(c) != 'Mn'])
    return texto.lower().strip()

def unificar():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "..", "app", "data")
    
    ins_path = os.path.join(data_dir, "alimentos_peru_ins.json")
    off_path = os.path.join(data_dir, "alimentos_peru_off.json")
    output_path = os.path.join(data_dir, "alimentos_peru_unificado.json")
    
    unificados = {}

    def cargar_y_unificar(path, fuente):
        if not os.path.exists(path):
            print(f"⚠️ No se encontró {path}")
            return
        
        with open(path, 'r', encoding='utf-8') as f:
            datos = json.load(f)
            
        for item in datos:
            nombre_raw = item.get("alimento") or item.get("nombre")
            if not nombre_raw: continue
            
            nombre_norm = normalizar_texto(nombre_raw)
            
            # Extraer macros con fallback
            kcal = float(item.get("calorias_100g", 0) or item.get("calorias", 0))
            prot = float(item.get("proteina_100g", 0) or item.get("proteinas", 0))
            carb = float(item.get("carbohindratos_100g", 0) or item.get("carbohidratos", 0))
            gras = float(item.get("grasas_100g", 0) or item.get("grasas", 0))
            fibra = float(item.get("fibra_100g", 0) or item.get("fibra", 0))
            azucar = float(item.get("azucar_100g", 0) or item.get("azucares", 0))
            
            if kcal <= 0 and prot <= 0 and carb <= 0: continue # Ignorar vacíos
            
            # Si ya existe, preferir el que tenga más info o sea verificado
            if nombre_norm in unificados:
                if unificados[nombre_norm]["kcal_por_100g"] > 0 and kcal > 0:
                    continue # Quedarse con el primero (INS suele ser más confiable para básicos)

            unificados[nombre_norm] = {
                "nombre": nombre_norm,
                "nombre_mostrar": nombre_raw,
                "kcal_por_100g": kcal,
                "proteinas_por_100g": prot,
                "carbos_por_100g": carb,
                "grasas_por_100g": gras,
                "fibra_por_100g": fibra,
                "azucar_por_100g": azucar,
                "peso_pieza_g": item.get("peso_pieza_g"),
                "peso_porcion_g": item.get("gramos", 100), # Fallback a 100g si no hay porción
                "categoria": item.get("categoria", "General"),
                "es_plato_peruano": "ins" in path.lower() or item.get("es_plato_peruano", False),
                "fuente": fuente
            }

    cargar_y_unificar(ins_path, "bd_local_ins")
    cargar_y_unificar(off_path, "bd_local_off")

    # Guardar resultado
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(list(unificados.values()), f, indent=4, ensure_ascii=False)
    
    print(f"✅ Unificación completada: {len(unificados)} alimentos únicos guardados en {output_path}")

if __name__ == "__main__":
    unificar()
