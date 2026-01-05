from datetime import date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import func
from sqlalchemy.orm.exc import NoResultFound
from typing import List, Optional

from dominio.modelos import PlanModel, SocioModel, MembresiaModel
from bd.conexion import engine
from aplicacion.serviciosMembresia import ServiciosMembresia
from Utilerias.util_qr import generar_qr_como_bytes

class ServiciosSocio():
    
    def __init__(self):      
        self.engine = engine

    def registrar(self, nombre: str, apellido_paterno: str, apellido_materno: str | None) -> Optional[SocioModel]:
        """Registra un nuevo socio sin membresía."""
        with Session(self.engine) as session:
            try:
                socio = SocioModel(nombre=nombre, apellido_paterno=apellido_paterno, apellido_materno=apellido_materno)
                session.add(socio)
                session.commit()
                session.refresh(socio)
                return socio
            except IntegrityError as e:
                session.rollback()
                raise ValueError("Ya existe un socio con estos datos")
            except Exception as e:
                session.rollback()
                raise Exception(f"Error interno al registrar socio: {e}")

    def obtener_socios_con_membresia(self) -> List[SocioModel]:
        """
        Obtiene todos los socios, precargando eficientemente sus membresías y los planes asociados.
        Esto previene errores de 'DetachedInstanceError' al acceder a relaciones fuera de la sesión.
        """
        with Session(self.engine) as session:
            # Usamos joinedload para cargar proactivamente las relaciones anidadas.
            # Socio -> Membresias -> Plan
            return session.query(SocioModel).options(joinedload(SocioModel.membresias).joinedload(MembresiaModel.plan)).all()

    def modificar(self, socio_id: int, nombre: str, apellido_paterno: str, apellido_materno: str | None,
                  foto_bytes: bytes | None = None, huella_template: bytes | None = None) -> bool:
        """Modifica los datos personales y foto/huella de un socio existente."""
        with Session(self.engine) as session:
            try:
                socio = session.query(SocioModel).filter_by(id=socio_id).one()
                
                # Actualizar datos personales
                socio.nombre = nombre
                socio.apellido_paterno = apellido_paterno
                socio.apellido_materno = apellido_materno
                
                # Actualizar foto si se proporciona
                if foto_bytes is not None:
                    if foto_bytes == b'':
                        socio.foto_ruta = None
                        print(f"Foto eliminada para socio ID {socio_id}")
                    elif len(foto_bytes) > 0:
                        socio.foto_ruta = foto_bytes
                        print(f"Foto actualizada para socio ID {socio_id}")
                # Actualizar huella si se proporciona
                if huella_template is not None:
                    if huella_template == b'':
                        socio.huella_template = None
                        print(f"Huella eliminada para socio ID {socio_id}")
                    elif len(huella_template) > 0:
                        socio.huella_template = huella_template
                        print(f"Huella actualizada para socio ID {socio_id}")
                
                session.commit()
                return True
            except NoResultFound:
                raise ValueError(f"No se encontró ningún socio con ID {socio_id}")
            except IntegrityError as e:
                session.rollback()
                # Podría ser por duplicidad de nombre u otra restricción, o por huella duplicada
                raise ValueError("Violación de integridad (posible duplicado de datos o huella)")
            except Exception as e:
                session.rollback()
                raise Exception(f"Error interno al modificar socio: {e}")

    def obtener_socios(self) -> List[SocioModel]:
        """Obtiene una lista de todos los socios."""
        # MODIFICADO: Ahora también carga las relaciones para consistencia.
        with Session(self.engine) as session:
            return session.query(SocioModel).options(
                joinedload(SocioModel.membresias).joinedload(MembresiaModel.plan)
            ).all()

    def eliminar(self, socio_id: int) -> bool:
        """
        Elimina un socio por su ID, aplicando reglas de negocio.
        - No permite eliminar socios con membresía activa.
        - Lanza ValueError con mensajes claros si no se puede eliminar.
        """
        with Session(self.engine) as session:
            try:
                # Usamos joinedload para traer las membresías eficientemente
                socio = session.query(SocioModel).options(
                    joinedload(SocioModel.membresias)
                ).filter_by(id=socio_id).one()

                # --- LÓGICA DE NEGOCIO MOVIDA AQUÍ ---
                if socio.membresias:
                    membresia_reciente = max(socio.membresias, key=lambda m: m.fecha_fin)
                    hoy = date.today()
                    
                    # Regla: No eliminar si la membresía está activa o vence hoy.
                    if membresia_reciente.fecha_fin >= hoy:
                        raise ValueError(
                            f"No se puede eliminar. El socio tiene una membresía activa o que vence hoy.\n"
                            f"Finaliza el: {membresia_reciente.fecha_fin.strftime('%d-%m-%Y')}."
                        )

                # Si pasa todas las validaciones, se procede a eliminar
                session.delete(socio)
                session.commit()
                return True

            except NoResultFound:
                session.rollback()
                raise ValueError(f"No se encontró ningún socio con ID {socio_id}")
            
            except ValueError as ve: # Re-lanzar la excepción de negocio que creamos
                session.rollback()
                raise ve

            except IntegrityError as e:
                session.rollback()
                if "FOREIGN KEY constraint failed" in str(e):
                     raise ValueError("No se puede eliminar el socio porque tiene registros asociados (posiblemente pagos o accesos).")
                raise ValueError("Error de integridad al intentar eliminar el socio.")
            except Exception as e:
                session.rollback()
                raise Exception(f"Error interno al eliminar socio: {e}")
    
    def obtener_socio_por_id(self, socio_id: int) -> Optional[SocioModel]:
        """Obtiene un único socio por su ID, precargando sus membresías y planes."""
        with Session(self.engine) as session:
            try:
                # Usamos joinedload para cargar proactivamente las relaciones anidadas.
                # Socio -> Membresias -> Plan
                return session.query(SocioModel).options(
                    joinedload(SocioModel.membresias).joinedload(MembresiaModel.plan)
                ).filter(SocioModel.id == socio_id).one_or_none()
            except Exception as e:
                print(f"Error al obtener socio por ID: {e}")
                return None
    
    def registrar_socio_con_membresia(self, nombre: str, apellido_paterno: str, apellido_materno: str | None,
                                      plan_id: int, fecha_inicio: date,
                                      foto_bytes: bytes | None = None, huella_template: bytes | None = None) -> Optional[SocioModel]:
        """
        Registra un nuevo socio y su primera membresía en una única transacción.
        Si algo falla, se deshace todo automáticamente.
        """
        with Session(self.engine) as session:
            # Instanciamos el servicio de membresías para usar su lógica
            servicio_membresia = ServiciosMembresia()
            # Obtenemos el objeto plan para el cálculo
            plan_obj = session.query(PlanModel).filter_by(id=plan_id).one()

            try:
                
                if fecha_inicio < date.today():
                    raise ValueError("La fecha de inicio no puede ser anterior a hoy")
                
                # Paso A: Crear el objeto Socio
                nuevo_socio = SocioModel(
                    nombre=nombre,
                    apellido_paterno=apellido_paterno,
                    apellido_materno=apellido_materno,
                    foto_ruta=foto_bytes,
                    huella_template=huella_template
                )
                session.add(nuevo_socio)
                session.flush()  # Asigna el ID preliminar

                # Paso A.2: Generar y asignar el código QR usando el ID recién asignado
                qr_data = f"socio_id:{nuevo_socio.id}"
                qr_bytes = generar_qr_como_bytes(qr_data)
                nuevo_socio.qr_code = qr_bytes

                # Paso B: Crear la membresía usando el ID del nuevo socio
                nueva_membresia = MembresiaModel(
                    socio_id=nuevo_socio.id,
                    plan_id=plan_id,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=servicio_membresia._calcular_fecha_fin(fecha_inicio, plan_obj)
                )
                session.add(nueva_membresia)

                session.commit()
                # Guardamos el ID antes de que el objeto se desvincule de la sesión
                nuevo_socio_id = nuevo_socio.id
                
                # En lugar de un 'refresh', volvemos a consultar el socio recién creado
                # usando 'joinedload' para cargar proactivamente todas las relaciones anidadas.
                # Esto evita el error de "lazy load" fuera de la sesión.
                socio_completo = session.query(SocioModel).options( 
                    joinedload(SocioModel.membresias).joinedload(MembresiaModel.plan)
                ).filter_by(id=nuevo_socio_id).one()
                
                return socio_completo 
            except IntegrityError as e:
                session.rollback()
                raise ValueError("Ya existe un socio con estos datos")
            except ValueError as e:
                session.rollback()
                raise e  # Re-lanzar errores de validación
            except Exception as e:
                session.rollback()
                raise Exception(f"Error interno al registrar socio con membresía: {e}")

    def buscar_por_nombre_aproximado(self, texto_busqueda: str) -> List[SocioModel]:
        """
        Busca socios cuyo nombre completo coincida de forma aproximada con el texto.
        Es insensible a mayúsculas/minúsculas.
        """
        with Session(self.engine) as session:
            try:
                # Construimos el término de búsqueda para que sea flexible
                termino = f"%{texto_busqueda.strip()}%"
                
                # Usamos func.concat para una concatenación segura en SQL.
                # Usamos func.coalesce para manejar el caso en que apellido_materno sea NULL,
                # reemplazándolo con una cadena vacía para que la concatenación no falle.
                return session.query(SocioModel).options(
                    # ¡SOLUCIÓN! Cargamos proactivamente las membresías y sus planes asociados.
                    joinedload(SocioModel.membresias).joinedload(MembresiaModel.plan)
                ).filter(
                    func.concat(
                        SocioModel.nombre, ' ', SocioModel.apellido_paterno, ' ', func.coalesce(SocioModel.apellido_materno, '')
                    ).ilike(termino)
                ).all()
            except Exception as e:
                raise Exception(f"Error al buscar socios: {e}")

    def obtener_socios_con_huella(self) -> List[SocioModel]:
        """Obtiene todos los socios que tienen una huella registrada."""
        with Session(self.engine) as session:
            return session.query(SocioModel).filter(SocioModel.huella_template.isnot(None)).all()

    def identificar_por_huella(self, fmd_capturado: bytes) -> Optional[SocioModel]:
        """
        Identifica a un socio comparando una huella capturada (FMD) con todas las
        huellas almacenadas en la base de datos (identificación 1-a-N).
        Devuelve el objeto SocioModel si encuentra una coincidencia, de lo contrario None.
        
        Este método adapta la identificación 1-a-N utilizando múltiples verificaciones 1-a-1
        con `dpHMatch.dll`, ya que `DPFPID.dll` no está disponible.
        """
        import ctypes
        import os
        import platform
        
        # Importar las DLLs necesarias para la comparación 1-a-1
        # Estas ya deberían estar cargadas en IdentificationWorker, pero las cargamos aquí
        # para asegurar que el servicio pueda funcionar de forma independiente si es necesario.
        try:
            dphmatch_dll = ctypes.WinDLL('dpHMatch.dll')
        except OSError as e:
            raise Exception(f"Error al cargar dpHMatch.dll: {e}. Asegúrese de que el RTE de DigitalPersona esté instalado.")

        # Definir tipos y constantes necesarios para dpHMatch.dll
        FT_HANDLE = ctypes.c_void_p
        FT_BYTE = ctypes.c_ubyte
        FT_BOOL = ctypes.c_int
        FT_REG_FTR = 1 # Para plantillas registradas
        FT_VER_FTR = 2 # Para plantillas de verificación (capturadas en vivo)

        # Prototipos para dpHMatch.dll (solo los necesarios para MC_verifyFeaturesEx)
        dphmatch_dll.MC_init.restype = ctypes.c_int
        dphmatch_dll.MC_createContext.argtypes = [ctypes.POINTER(FT_HANDLE)]
        dphmatch_dll.MC_createContext.restype = ctypes.c_int
        dphmatch_dll.MC_getFeaturesLen.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
        dphmatch_dll.MC_getFeaturesLen.restype = ctypes.c_int
        dphmatch_dll.MC_verifyFeaturesEx.argtypes = [FT_HANDLE, ctypes.c_int, ctypes.POINTER(FT_BYTE), ctypes.c_int, ctypes.POINTER(FT_BYTE), ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_double), ctypes.POINTER(FT_BOOL)]
        dphmatch_dll.MC_verifyFeaturesEx.restype = ctypes.c_int
        dphmatch_dll.MC_closeContext.argtypes = [FT_HANDLE]
        dphmatch_dll.MC_closeContext.restype = ctypes.c_int
        dphmatch_dll.MC_terminate.restype = ctypes.c_int

        if platform.system().lower() != "windows":
            print("La identificación por huella solo es compatible con Windows.")
            return None

        mc_context = FT_HANDLE(0)
        try:
            # Inicializar el contexto de MC
            if dphmatch_dll.MC_init() != 0: raise Exception("Fallo al inicializar MC_init")
            if dphmatch_dll.MC_createContext(ctypes.byref(mc_context)) != 0: raise Exception("Fallo al crear contexto MC")

            # Obtener la longitud esperada para las características de verificación
            ver_feature_len_ptr = ctypes.c_int(0)
            # Asumimos que FT_VER_FTR tiene una longitud estándar que se puede obtener de FX_getFeaturesLen
            # Sin embargo, aquí solo necesitamos el tamaño de la plantilla que nos llega (fmd_capturado)
            # y el tamaño de las plantillas de registro (huella_template de SocioModel).
            # La longitud de la plantilla de verificación (fmd_capturado) ya la tenemos.
            
            # Preparar la plantilla de verificación (la capturada en vivo)
            ver_buffer = (FT_BYTE * len(fmd_capturado)).from_buffer_copy(fmd_capturado)

            socios_con_huella = self.obtener_socios_con_huella()
            if not socios_con_huella:
                return None

            # Iterar sobre todas las plantillas guardadas
            for socio in socios_con_huella:
                if not socio.huella_template:
                    continue # Saltar si el socio no tiene huella

                reg_template_buffer = (FT_BYTE * len(socio.huella_template)).from_buffer_copy(socio.huella_template)
                comparison_decision = FT_BOOL(0)
                achieved_far = ctypes.c_double(0.0)

                rc = dphmatch_dll.MC_verifyFeaturesEx(
                    mc_context, len(socio.huella_template), ctypes.cast(reg_template_buffer, ctypes.POINTER(FT_BYTE)),
                    len(fmd_capturado), ctypes.cast(ver_buffer, ctypes.POINTER(FT_BYTE)),
                    0, None, None, None, ctypes.byref(achieved_far), ctypes.byref(comparison_decision)
                )

                # Si hay coincidencia, devolver el socio inmediatamente
                if rc == 0 and comparison_decision.value == 1:
                    return self.obtener_socio_por_id(socio.id)
            
            # Si no se encontró ninguna coincidencia después de iterar todas las huellas
            return None

        except Exception as e:
            raise Exception(f"Error durante la identificación por huella: {e}")
        finally:
            # Limpiar el contexto de MC
            if mc_context and mc_context.value:
                dphmatch_dll.MC_closeContext(mc_context)
            dphmatch_dll.MC_terminate()