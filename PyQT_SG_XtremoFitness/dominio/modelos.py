from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, BLOB
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class SocioModel(Base):
    __tablename__ = "Socios"
    id = Column("ID", Integer, primary_key=True, autoincrement=True)
    nombre = Column("Nombre", String(150), nullable=False)
    apellido_paterno = Column("Apellido_Paterno", String(150), nullable=False)
    apellido_materno = Column("Apellido_Materno", String(150))
    foto_ruta = Column("Foto_Ruta", BLOB)
    huella_template = Column("Huella_Template", BLOB, unique=True)
    qr_code = Column("QR_Code", BLOB) 
    
    membresias = relationship("MembresiaModel", back_populates="socio", cascade="all, delete-orphan")

class PlanModel(Base):
    __tablename__ = "Planes"
    id = Column("ID", Integer, primary_key=True, autoincrement=True)
    nombre = Column("Nombre", String(100), unique=True, nullable=False)
    precio = Column("Precio", Float, nullable=False)
    duracion_dias = Column("Duracion_Dias", Integer, nullable=False) # Necesario para los cálculos

    membresias = relationship("MembresiaModel", back_populates="plan")

class MembresiaModel(Base):
    __tablename__ = "Membresias"
    id = Column("ID", Integer, primary_key=True, autoincrement=True)
    socio_id = Column("Socio_ID", Integer, ForeignKey("Socios.ID"), nullable=False)
    plan_id = Column("Plan_ID", Integer, ForeignKey("Planes.ID"), nullable=False)
    fecha_inicio = Column("Fecha_Inicio", Date, nullable=False)
    fecha_fin = Column("Fecha_Fin", Date, nullable=False)
    
    socio = relationship("SocioModel", back_populates="membresias")
    plan = relationship("PlanModel", back_populates="membresias")