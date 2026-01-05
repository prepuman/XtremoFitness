import sqlalchemy as db
from sqlalchemy.orm import Session
from dominio.modelos import PlanModel
from typing import List, Optional
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from bd.conexion import engine

class ServiciosPlan():
    
    def __init__(self):        
        self.engine = engine

    def registrar(self, nombre: str, precio: float, duracion_dias: int) -> Optional[PlanModel]:
        with Session(self.engine) as session:
            try:
                plan = PlanModel(nombre=nombre, precio=precio, duracion_dias=duracion_dias)
                session.add(plan)
                session.commit()
                session.refresh(plan)
                return plan
            except Exception as e:
                session.rollback(); print(f"Error al registrar plan: {e}"); return None
    
    def modificar(self, plan_id: int, nombre: str, precio: float, duracion_dias: int) -> bool:
        with Session(self.engine) as session:
            try:
                plan = session.query(PlanModel).filter_by(id=plan_id).one()
                plan.nombre = nombre
                plan.precio = precio
                plan.duracion_dias = duracion_dias
                session.commit()
                return True
            except NoResultFound: return False
            except Exception as e: session.rollback(); print(f"Error al modificar plan: {e}"); return False

    def obtener_planes(self) -> List[PlanModel]:
        with Session(self.engine) as session:
            return session.query(PlanModel).all()
            
    def obtener_plan_por_nombre(self, nombre: str) -> Optional[PlanModel]:
        with Session(self.engine) as session:
            return session.query(PlanModel).filter_by(nombre=nombre).one_or_none()

    def obtener_plan_por_id(self, plan_id: int) -> Optional[PlanModel]:
        with Session(self.engine) as session:
            return session.query(PlanModel).filter_by(id=plan_id).one_or_none()

    def eliminar(self, plan_id: int) -> bool:
        with Session(self.engine) as session:
            try:
                plan = session.query(PlanModel).filter_by(id=plan_id).one()
                session.delete(plan)
                session.commit()
                return True
            except Exception as e:
                session.rollback(); print(f"Error al eliminar plan: {e}"); return False