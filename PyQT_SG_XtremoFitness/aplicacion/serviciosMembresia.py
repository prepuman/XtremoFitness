import sqlalchemy as db
from sqlalchemy.orm import Session, joinedload
from dominio.modelos import MembresiaModel, PlanModel, SocioModel
from datetime import date, timedelta
from typing import Optional
from bd.conexion import engine
from dateutil.relativedelta import relativedelta


class ServiciosMembresia:
    def __init__(self):
        self.engine = engine
        
    def registrar_membresia(self, socio_id: int, plan_id: int, fecha_inicio: date, fecha_fin: date) -> Optional[MembresiaModel]:
        with Session(self.engine) as session:
            try:
                membresia = MembresiaModel(socio_id=socio_id, plan_id=plan_id, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)
                session.add(membresia)
                session.commit()
                return membresia
            except Exception as e:
                session.rollback()
                print(f"Error al registrar la membresía: {e}")
                return None

    def renovar_membresia(self, socio_id: int, plan_id: int) -> Optional[MembresiaModel]:
        """Crea una nueva membresía para un socio existente (renovación)."""
        with Session(self.engine) as session:
            try:
                plan_obj = session.query(PlanModel).filter_by(id=plan_id).one()
                fecha_inicio = date.today()
                fecha_fin = self._calcular_fecha_fin(fecha_inicio, plan_obj)

                nueva_membresia = MembresiaModel(socio_id=socio_id, plan_id=plan_id, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)
                session.add(nueva_membresia)
                session.commit()
                
                # --- SOLUCIÓN AL ERROR 'DetachedInstanceError' ---
                # En lugar de devolver el objeto 'nueva_membresia' que se desconectará de la sesión,
                # lo volvemos a consultar inmediatamente, pero esta vez cargando proactivamente
                # sus relaciones ('plan' y 'socio').
                membresia_completa = session.query(MembresiaModel).options(
                    joinedload(MembresiaModel.plan),
                    joinedload(MembresiaModel.socio)
                ).filter_by(id=nueva_membresia.id).one()
                
                return membresia_completa
            except Exception as e:
                session.rollback()
                raise Exception(f"Error al renovar la membresía: {e}")

    def calcular_estatus_membresia(self, fecha_fin: date) -> str:
        """
        Calcula el estatus de la membresía basado en su fecha de finalización.
        """
        hoy = date.today()
        dias_restantes = (fecha_fin - hoy).days
        
        if dias_restantes < 0:
            return "Vencido"
        elif dias_restantes == 0:
            return "Vence Hoy"
        elif dias_restantes <= 7:
            return f"Por Vencer ({dias_restantes} días)"
        else:
            return "Activo"

    def _calcular_fecha_fin(self, fecha_inicio: date, plan_obj: PlanModel) -> date:
        """Calcula la fecha de vencimiento basado en la duración del plan."""
        if not hasattr(plan_obj, 'duracion_dias') or plan_obj.duracion_dias <= 0:
            raise ValueError("El plan seleccionado tiene una duración inválida.")

        duracion = plan_obj.duracion_dias

        # Si la duración es un múltiplo de 30, usar meses para mayor precisión
        # (ej. 30, 60, 90 días se convierten en 1, 2, 3 meses)
        if duracion % 30 == 0:
            meses = duracion // 30
            return fecha_inicio + relativedelta(months=meses) - timedelta(days=1)
        else:
            # Para duraciones irregulares (ej. 7, 15 días), usar días
            return fecha_inicio + timedelta(days=duracion - 1)