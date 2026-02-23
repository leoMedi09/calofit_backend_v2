from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.client import Client
from app.models.user import User
from app.api.routes.auth import get_current_user
from app.services.ia_service import IAService
from app.models.nutricion import PlanNutricional, PlanDiario
from app.schemas.nutricion import PlanNutricionalResponse, PlanNutricionalUpdate

router = APIRouter()
ia_service = IAService()

def check_is_nutri(current_user: User):
    role = str(getattr(current_user, "role_name", "")).lower()
    if role not in ["nutricionista", "admin", "administrador"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operación permitida solo para Nutricionistas o Administradores"
        )
    return current_user

@router.get("/clientes", response_model=List[dict])
def get_assigned_patients(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_is_nutri(current_user)
    
    # Si es Admin, ve todos los clientes. Si es Nutri, solo los suyos.
    query = db.query(Client)
    role = str(getattr(current_user, "role_name", "")).lower()
    if role == "nutricionista":
        query = query.filter(Client.assigned_nutri_id == current_user.id)
    
    clients = query.all()
    
    from datetime import datetime, timedelta
    seven_days_ago = datetime.now() - timedelta(days=7)
    
    result = []
    for c in clients:
        # Lógica de adherencia real: Contar días con registros en los últimos 7 días
        registros_recientes = [r for r in c.progreso_calorias if r.fecha >= seven_days_ago.date()]
        num_registros = len(registros_recientes)
        
        adherencia = round((num_registros / 7) * 100, 1)
        progreso = 50.0 # TODO: Calcular progreso real basado en tendencia de peso
        
        alerta = ia_service.generar_alerta_fuzzy(adherencia, progreso)
        
        result.append({
            "id": c.id,
            "full_name": f"{c.first_name} {c.last_name_paternal} {c.last_name_maternal}",
            "email": c.email,
            "goal": c.goal,
            "weight": c.weight,
            "adherencia": adherencia,
            "alerta": alerta,
            "gender": c.gender
        })
    
    return result

@router.get("/cliente/{id}/progreso")
def get_patient_progress(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_is_nutri(current_user)
    
    client = db.query(Client).filter(Client.id == id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
    # Verificar que el nutri tenga acceso
    if current_user.role_name.upper() == "NUTRICIONISTA" and client.assigned_nutri_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver este paciente")

    # Obtener historial de peso, imc y progreso calórico
    historial_peso = [{"fecha": h.fecha, "valor": h.peso} for h in client.historial_peso]
    historial_imc = [{"fecha": h.fecha, "valor": h.imc} for h in client.historial_imc]
    
    return {
        "client_id": client.id,
        "full_name": f"{client.first_name} {client.last_name_paternal}",
        "historial_peso": historial_peso,
        "historial_imc": historial_imc,
        "current_weight": client.weight,
        "current_height": client.height,
    }

@router.post("/validar-plan/{id}")
def validate_plan(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_is_nutri(current_user)
    # Lógica para cambiar status de plan a 'validado'
    plan = db.query(PlanNutricional).filter(PlanNutricional.client_id == id).order_by(PlanNutricional.fecha_creacion.desc()).first()
    if plan:
        plan.status = "validado"
        plan.validated_by_id = current_user.id
        plan.validated_at = datetime.utcnow()
        db.commit()
    return {"message": f"Plan del cliente {id} validado correctamente por Nutricionista {current_user.first_name}"}

@router.get("/cliente/{id}/plan", response_model=PlanNutricionalResponse)
def get_client_plan(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_is_nutri(current_user)
    client = db.query(Client).filter(Client.id == id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
    if current_user.role_name.upper() == "NUTRICIONISTA" and client.assigned_nutri_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver este paciente")
    
    plan = db.query(PlanNutricional).filter(PlanNutricional.client_id == id).order_by(PlanNutricional.fecha_creacion.desc()).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Este paciente aún no tiene un plan nutricional asignado")
    return plan

@router.put("/cliente/{id}/plan")
def update_client_plan(
    id: int,
    plan_update: PlanNutricionalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_is_nutri(current_user)
    client = db.query(Client).filter(Client.id == id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
    if current_user.role_name.upper() == "NUTRICIONISTA" and client.assigned_nutri_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso")
    
    plan = db.query(PlanNutricional).filter(PlanNutricional.client_id == id).order_by(PlanNutricional.fecha_creacion.desc()).first()
    if not plan:
        raise HTTPException(status_code=404, detail="No hay plan para actualizar")
    
    if plan_update.objetivo:
        plan.objetivo = plan_update.objetivo
    if plan_update.observaciones:
        plan.observaciones = plan_update.observaciones
    if plan_update.status:
        plan.status = plan_update.status
        
    if plan_update.detalles_diarios:
        for i, daily_update in enumerate(plan_update.detalles_diarios):
            if i < len(plan.detalles_diarios):
                daily = plan.detalles_diarios[i]
                if daily_update.calorias_dia is not None:
                    daily.calorias_dia = daily_update.calorias_dia
                if daily_update.proteinas_g is not None:
                    daily.proteinas_g = daily_update.proteinas_g
                if daily_update.carbohidratos_g is not None:
                    daily.carbohidratos_g = daily_update.carbohidratos_g
                if daily_update.grasas_g is not None:
                    daily.grasas_g = daily_update.grasas_g
                daily.estado = daily_update.estado or "oficial"
    
    db.commit()
    return {"message": "Plan actualizado exitosamente"}
