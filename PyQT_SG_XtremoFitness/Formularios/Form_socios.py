from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QFrame, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QMessageBox, QComboBox, QGridLayout, QFileDialog)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import base64
from PIL import Image
import io
import sys
from Utilerias.util_foto import abrir_camara_sistema, cargar_foto_desde_archivo



# Importamos las clases de servicios
from aplicacion.serviciosSocio import ServiciosSocio
from aplicacion.serviciosPlan import ServiciosPlan
from aplicacion.serviciosMembresia import ServiciosMembresia
from config import *
from .Dialogo_Credencial import DialogoCredencial
from Utilerias.captura_huella import EnrollmentWorker
from Utilerias.generador_pdf import generar_voucher_socio, abrir_archivo
from Utilerias.util_imagenes import procesar_imagen_para_perfil

class SocioRegistro(QWidget):
    def __init__(self, master=None):
        super().__init__(master)
        
        # Guardará el nombre del plan cuando se seleccione un socio
        self.plan_original_seleccionado = None
        
        self.servicio_socios = ServiciosSocio()
        self.servicio_planes = ServiciosPlan()
        self.servicio_membresia = ServiciosMembresia()
        
        self._crear_ui()
        self._conectar_senales()
        
        self.actualizar_lista()
        self.limpiar_campos()
        self.cargar_planes_en_combobox()

        # Para manejar el hilo de la huella
        self.enrollment_thread = None
        # Inicializamos huella_actual a None para evitar AttributeError
        self.huella_actual = None

    def _crear_line_edit(self, placeholder="", read_only=False):
        """Función auxiliar para crear y estilizar QLineEdit."""
        line_edit = QLineEdit()
        line_edit.setPlaceholderText(placeholder)
        line_edit.setReadOnly(read_only)
        return line_edit

    def _crear_ui(self):
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(20, 20, 20, 20); layout_principal.setSpacing(15)
        self.setStyleSheet(f"background-color: {COLOR_FONDO}; color: white; font-size: 14px;")

        label_titulo = QLabel("GESTIÓN DE SOCIOS")
        label_titulo.setStyleSheet(f"font-size: 24px; font-weight: bold; color: white; background-color: {COLOR_TITULO}; padding: 10px; border-radius: 5px;")
        label_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(label_titulo)

         # --- Barra de Botones ---
        marco_botones = QFrame(); layout_botones = QHBoxLayout(marco_botones)
        
        # --- Barra de Búsqueda (usando la nueva función auxiliar) ---
        self.campo_busqueda = self._crear_line_edit("Ingresa nombre o apellido del socio")
        self.campo_busqueda.setStyleSheet("background-color: white; color: black; border-radius: 4px; padding: 5px;") # Estilo específico
        self.btn_buscar = QPushButton()
        self.btn_buscar.setFixedSize(35, 35)
        self.btn_buscar.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_BTN_BUSCAR};
                color: white;
                font-size: 16px;
                border-radius: 4px;
                image: url(./Iconos/lupa.svg); /* Establecer la imagen de fondo */
                background-repeat: no-repeat; /* Evitar que la imagen se repita */
                background-position: center; /* Centrar la imagen */
                border: none; /* Elimina el borde predeterminado del botón */
                padding: 5px; /* Añade un espacio interior para hacer el icono más pequeño */
            }}
             QPushButton:hover {{
                background-color: #555;
            }}
            QPushButton:pressed {{
                background-color: #333;
            }}
        """)
        
        layout_botones.addWidget(self.campo_busqueda)
        layout_botones.addWidget(self.btn_buscar)
        layout_botones.addStretch() # Empuja los otros botones a la derecha

        self.btn_registrar = QPushButton("Registrar")
        self.btn_modificar = QPushButton("Modificar")
        self.btn_eliminar = QPushButton("Eliminar")
        self.btn_imprimir = QPushButton("Imprimir Voucher")
        self.btn_limpiar = QPushButton("Limpiar Campos")
        
        self.btn_registrar.setStyleSheet(f"background-color: {COLOR_BTN_REGISTRAR}; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")
        self.btn_modificar.setStyleSheet(f"background-color: {COLOR_BTN_MODIFICAR}; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")
        self.btn_eliminar.setStyleSheet(f"background-color: {COLOR_BTN_ELIMINAR}; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")
        self.btn_imprimir.setStyleSheet(f"background-color: {COLOR_BTN_IMPRIMIR}; color: white; padding: 8px; border-radius: 4px; font-weight: bold;") 
        self.btn_limpiar.setStyleSheet(f"background-color: {COLOR_LIMPIAR_CAMPOS}; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")

        layout_botones.addWidget(self.btn_limpiar); layout_botones.addWidget(self.btn_imprimir)
        layout_botones.addWidget(self.btn_eliminar); layout_botones.addWidget(self.btn_modificar)
        layout_botones.addWidget(self.btn_registrar)
        layout_principal.addWidget(marco_botones)

        # --- Marco de Información 
        marco_info = QFrame(); layout_info = QHBoxLayout(marco_info)
        frame_foto = QFrame(); layout_foto = QVBoxLayout(frame_foto); layout_foto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Espacio para foto con botones
        self.label_foto = QLabel("Sin Foto")
        self.label_foto.setFixedSize(150, 150)
        self.label_foto.setStyleSheet("""
            QLabel {
                background-color: #333; 
                border: 2px solid #555; 
                border-radius: 5px;
                color: #AAA;
                font-size: 12px;
            }
        """)
        self.label_foto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_foto.setScaledContents(True)
        
        # Botones para foto
        frame_botones_foto = QFrame()
        layout_botones_foto = QHBoxLayout(frame_botones_foto)
        layout_botones_foto.setContentsMargins(0, 5, 0, 0)
        
        self.btn_tomar_foto = QPushButton()
        self.btn_cargar_foto = QPushButton()
        self.btn_eliminar_foto = QPushButton()
        
        # Estilos para botones de foto
        estilo_tomarfoto = f"""
            QPushButton {{
                background-color: {COLOR_TOMARFOTO};
                color: white;
                border: 1px solid #666;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 10px;
                font-weight: bold;
                image: url(./Iconos/camara.svg); /* Establecer la imagen de fondo */
                background-repeat: no-repeat; /* Evitar que la imagen se repita */
                background-position: center; /* Centrar la imagen */
                border: none; /* Elimina el borde predeterminado del botón */
                padding: 5px; /* Añade un espacio interior para hacer el icono más pequeño */
            }}
            QPushButton:hover {{
                background-color: #555;
            }}
            QPushButton:pressed {{
                background-color: #333;
            }}
        """
        estilo_cargarfoto = f"""
            QPushButton {{
                background-color: {COLOR_CARGARFOTO};
                color: white;
                border: 1px solid #666;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 10px;
                font-weight: bold;
                image: url(./Iconos/folder.svg); /* Establecer la imagen de fondo */
                background-repeat: no-repeat; /* Evitar que la imagen se repita */
                background-position: center; /* Centrar la imagen */
                border: none; /* Elimina el borde predeterminado del botón */
                padding: 5px; /* Añade un espacio interior para hacer el icono más pequeño */
            }}
            QPushButton:hover {{
                background-color: #555;
            }}
            QPushButton:pressed {{
                background-color: #333;
            }}
        """
        estilo_eliminarfoto = f"""
            QPushButton {{
                background-color: {COLOR_ELIMINARFOTO};
                color: white;
                border: 1px solid #666;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 10px;
                font-weight: bold;
                image: url(./Iconos/basura.svg); /* Establecer la imagen de fondo */
                background-repeat: no-repeat; /* Evitar que la imagen se repita */
                background-position: center; /* Centrar la imagen */
                border: none; /* Elimina el borde predeterminado del botón */
                padding: 5px; /* Añade un espacio interior para hacer el icono más pequeño */
            }}
            QPushButton:hover {{
                background-color: #555;
            }}
            QPushButton:pressed {{
                background-color: #333;
            }}
        """
        
        self.btn_tomar_foto.setStyleSheet(estilo_tomarfoto)
        self.btn_cargar_foto.setStyleSheet(estilo_cargarfoto)
        self.btn_eliminar_foto.setStyleSheet(estilo_eliminarfoto)
        
        # Tamaño de botones
        self.btn_tomar_foto.setFixedHeight(25)
        self.btn_cargar_foto.setFixedHeight(25)
        self.btn_eliminar_foto.setFixedHeight(25)
        
        layout_botones_foto.addWidget(self.btn_tomar_foto)
        layout_botones_foto.addWidget(self.btn_cargar_foto)
        layout_botones_foto.addWidget(self.btn_eliminar_foto)
        
        layout_foto.addWidget(self.label_foto)
        layout_foto.addWidget(frame_botones_foto)
        layout_info.addWidget(frame_foto, 1)
        
        # Variable para almacenar la foto actual
        self.foto_actual = None
        frame_formulario_central = QFrame(); layout_formulario_central = QHBoxLayout(frame_formulario_central)
        frame_personales = QFrame(); layout_personales = QGridLayout(frame_personales)
        layout_personales.addWidget(QLabel("Id:"), 0, 0); self.campo_id = self._crear_line_edit(read_only=True); self.campo_id.setStyleSheet("background-color: #333; color: #CCC; border-radius: 4px; padding: 5px;"); layout_personales.addWidget(self.campo_id, 0, 1)
        layout_personales.addWidget(QLabel("Nombre:"), 1, 0); self.campo_nombre = self._crear_line_edit("Nombre del socio"); self.campo_nombre.setStyleSheet("background-color: white; color: black; border-radius: 4px; padding: 5px;"); layout_personales.addWidget(self.campo_nombre, 1, 1)
        layout_personales.addWidget(QLabel("Apellido Paterno:"), 2, 0); self.campo_apellido_paterno = self._crear_line_edit("Apellido paterno"); self.campo_apellido_paterno.setStyleSheet("background-color: white; color: black; border-radius: 4px; padding: 5px;"); layout_personales.addWidget(self.campo_apellido_paterno, 2, 1)
        layout_personales.addWidget(QLabel("Apellido Materno:"), 3, 0); self.campo_apellido_materno = self._crear_line_edit("Apellido materno (opcional)"); self.campo_apellido_materno.setStyleSheet("background-color: white; color: black; border-radius: 4px; padding: 5px;"); layout_personales.addWidget(self.campo_apellido_materno, 3, 1)
        layout_formulario_central.addWidget(frame_personales)
        frame_membresia = QFrame(); layout_membresia = QGridLayout(frame_membresia)
        layout_membresia.addWidget(QLabel("Membresía:"), 0, 0); self.combo_membresia = QComboBox(); self.combo_membresia.setStyleSheet("background-color: white; color: black; border-radius: 4px; padding: 5px;"); layout_membresia.addWidget(self.combo_membresia, 0, 1)
        layout_membresia.addWidget(QLabel("Fecha Inicio:"), 1, 0); self.campo_fecha_ini = self._crear_line_edit(read_only=True); self.campo_fecha_ini.setStyleSheet("background-color: #333; color: #CCC; border-radius: 4px; padding: 5px;"); layout_membresia.addWidget(self.campo_fecha_ini, 1, 1)
        layout_membresia.addWidget(QLabel("Fecha Fin:"), 2, 0); self.campo_fecha_fin = self._crear_line_edit(read_only=True); self.campo_fecha_fin.setStyleSheet("background-color: #333; color: #CCC; border-radius: 4px; padding: 5px;"); layout_membresia.addWidget(self.campo_fecha_fin, 2, 1)
        layout_membresia.addWidget(QLabel("Estatus:"), 3, 0); self.campo_estatus = self._crear_line_edit(read_only=True); self.campo_estatus.setStyleSheet("background-color: #333; color: #CCC; border-radius: 4px; padding: 5px;"); layout_membresia.addWidget(self.campo_estatus, 3, 1)
        layout_formulario_central.addWidget(frame_membresia)
        layout_info.addWidget(frame_formulario_central, 2)
        frame_huella = QFrame()
        layout_huella = QVBoxLayout(frame_huella)
        layout_huella.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_huella = QLabel("Sin Huella")
        self.label_huella.setFixedSize(150, 150)
        self.label_huella.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_huella.setStyleSheet("background-color: #333; border: 1px solid #555; border-radius: 5px;")
        layout_huella.addWidget(self.label_huella)

        # Botones de huella
        frame_botones_huella = QFrame()
        layout_botones_huella = QHBoxLayout(frame_botones_huella)
        layout_botones_huella.setContentsMargins(0, 5, 0, 0)
        self.btn_capturar_huella = QPushButton()
        self.btn_eliminar_huella = QPushButton()
        estilo_tomarhuella = f"""
            QPushButton {{
                background-color: {COLOR_TOMARHUELLA};
                color: white;
                border: 1px solid #666;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 10px;
                font-weight: bold;
                image: url(./Iconos/huella.svg); /* Establecer la imagen de fondo */
                background-repeat: no-repeat; /* Evitar que la imagen se repita */
                background-position: center; /* Centrar la imagen */
                border: none; /* Elimina el borde predeterminado del botón */
                padding: 5px; /* Añade un espacio interior para hacer el icono más pequeño */
            }}
            QPushButton:hover {{
                background-color: #555;
            }}
            QPushButton:pressed {{
                background-color: #333;
            }}
        """
        estilo_eliminarhuella = f"""
            QPushButton {{
                background-color: {COLOR_ELIMINARHUELLA};
                color: white;
                border: 1px solid #666;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 10px;
                font-weight: bold;
                image: url(./Iconos/basura.svg); /* Establecer la imagen de fondo */
                background-repeat: no-repeat; /* Evitar que la imagen se repita */
                background-position: center; /* Centrar la imagen */
                border: none; /* Elimina el borde predeterminado del botón */
                padding: 5px; /* Añade un espacio interior para hacer el icono más pequeño */
            }}
            QPushButton:hover {{
                background-color: #555;
            }}
            QPushButton:pressed {{
                background-color: #333;
            }}
        """
        self.btn_capturar_huella.setStyleSheet(estilo_tomarhuella)
        self.btn_eliminar_huella.setStyleSheet(estilo_eliminarhuella)
        self.btn_capturar_huella.setFixedHeight(25)
        self.btn_eliminar_huella.setFixedHeight(25)
        layout_botones_huella.addWidget(self.btn_capturar_huella)
        layout_botones_huella.addWidget(self.btn_eliminar_huella)
        layout_huella.addWidget(frame_botones_huella)

        layout_info.addWidget(frame_huella, 1)
        layout_principal.addWidget(marco_info)

        # --- Tabla de Socios 
        self.tabla_socios = QTableWidget()
        self.tabla_socios.setColumnCount(6)
        self.tabla_socios.setHorizontalHeaderLabels(["ID", "Nombre Completo", "Plan Actual", "Inicio", "Vencimiento", "Estatus"])
        self.tabla_socios.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_socios.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_socios.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_socios.setStyleSheet(f"""
            QTableWidget {{ background-color: #FFFFFF; color: #000000; gridline-color: #D0D0D0; }}
            QHeaderView::section {{ background-color: {COLOR_BARRA_SUPERIOR}; color: white; padding: 4px; border: 1px solid {COLOR_BARRA_SUPERIOR}; font-weight: bold; }}
            QTableWidget::item:selected {{ background-color: {COLOR_MENU_CURSOR_ENCIMA}; color: white; }}
        """)
        layout_principal.addWidget(self.tabla_socios)
         # Oculta la primera columna (índice 0), que es la del ID.
        self.tabla_socios.setColumnHidden(0, True)

    def _conectar_senales(self):
        self.btn_registrar.clicked.connect(self.registrar_socio_y_membresia)
        self.btn_modificar.clicked.connect(self.modificar_socios)
        # Se elimina la conexión del botón renovar
        self.btn_eliminar.clicked.connect(self.eliminar_socios)
        self.btn_imprimir.clicked.connect(self.imprimir_voucher) 
        self.btn_limpiar.clicked.connect(self.limpiar_campos)
        self.tabla_socios.itemClicked.connect(self.al_seleccionar_tabla)
        
        # Conectar botones de foto
        self.btn_tomar_foto.clicked.connect(self.tomar_foto)
        self.btn_cargar_foto.clicked.connect(self.cargar_foto_archivo)
        self.btn_eliminar_foto.clicked.connect(self.eliminar_foto)

        # Conectar botones de huella
        self.btn_capturar_huella.clicked.connect(self.capturar_huella)
        self.btn_eliminar_huella.clicked.connect(self.eliminar_huella)

        # Conectar búsqueda 
        self.btn_buscar.clicked.connect(self.buscar_socio)
        # Permite buscar con "Enter"
        self.campo_busqueda.returnPressed.connect(self.buscar_socio) 

    def validar_nombre(self, nombre: str) -> bool:
        """Valida que el nombre contenga solo letras y espacios"""
        if not nombre or len(nombre.strip()) < 2:
            return False
        return nombre.replace(" ", "").isalpha()

    def validar_datos_socio(self, nombre: str, apellido_paterno: str, apellido_materno: str = "") -> tuple[bool, str]:
        """Valida todos los datos del socio"""
        # Validar nombre
        if not self.validar_nombre(nombre):
            return False, "El nombre debe tener al menos 2 caracteres y solo contener letras"
        
        # Validar apellido paterno
        if not self.validar_nombre(apellido_paterno):
            return False, "El apellido paterno debe tener al menos 2 caracteres y solo contener letras"
        
        # Validar apellido materno (opcional)
        if apellido_materno and not self.validar_nombre(apellido_materno):
            return False, "El apellido materno solo puede contener letras"
        
        return True, "Datos válidos"

    def validar_plan_seleccionado(self, plan_nombre: str) -> tuple[bool, str, object]:
        """Valida que el plan seleccionado sea válido"""
        if not plan_nombre:
            return False, "Debe seleccionar un plan de membresía", None
        
        try:
            plan_obj = self.servicio_planes.obtener_plan_por_nombre(plan_nombre)
            if not plan_obj:
                return False, f"No se encontró el plan '{plan_nombre}'. Verifique que el plan existe.", None
            
            if plan_obj.duracion_dias <= 0:
                return False, f"El plan '{plan_nombre}' tiene una duración inválida", None
            
            return True, "Plan válido", plan_obj
        except Exception as e:
            return False, f"Error al validar el plan: {e}", None

    # El método cargar_planes_en_combobox no se modifica
    def cargar_planes_en_combobox(self):
        try:
            self.combo_membresia.clear()
            planes = self.servicio_planes.obtener_planes()
            if planes:
                nombres_planes = [plan.nombre for plan in planes]
                self.combo_membresia.addItems(nombres_planes)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los planes: {e}")

    def registrar_socio_y_membresia(self):
        """Registra un nuevo socio con validaciones robustas"""
        try:
            # Obtener datos de los campos
            nombre = self.campo_nombre.text().strip()
            apellido_paterno = self.campo_apellido_paterno.text().strip()
            apellido_materno = self.campo_apellido_materno.text().strip()
            plan_nombre = self.combo_membresia.currentText()
            
            # Validar campos obligatorios
            if not nombre or not apellido_paterno or not plan_nombre:
                QMessageBox.warning(self, "Error", "Nombre, Apellido Paterno y Membresía son obligatorios.")
                return
            
            # Validar datos del socio
            es_valido, mensaje = self.validar_datos_socio(nombre, apellido_paterno, apellido_materno)
            if not es_valido:
                QMessageBox.warning(self, "Error de Validación", mensaje)
                return
            
            # Validar plan seleccionado
            es_plan_valido, mensaje_plan, plan_obj = self.validar_plan_seleccionado(plan_nombre)
            if not es_plan_valido:
                QMessageBox.critical(self, "Error de Plan", mensaje_plan)
                return
            
            # Calcular fechas
            fecha_inicio = date.today()
            # La fecha de fin ahora se calcula dentro del servicio
            
            # Registrar socio con membresía y foto
            nuevo_socio = self.servicio_socios.registrar_socio_con_membresia(
                nombre=nombre, 
                apellido_paterno=apellido_paterno,
                apellido_materno=apellido_materno,
                plan_id=plan_obj.id, 
                fecha_inicio=fecha_inicio, 
                foto_bytes=self.foto_actual,
                huella_template=self.huella_actual
            )
            
            if nuevo_socio:
                # PREGUNTAR SI SE DESEA IMPRIMIR DESPUÉS DEL ÉXITO ---
                respuesta = QMessageBox.question(
                    self, "Imprimir Comprobante",
                    f"Socio '{nuevo_socio.nombre}' registrado exitosamente.\n"
                    f"¿Desea imprimir el comprobante de inscripción ahora?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if respuesta == QMessageBox.StandardButton.Yes:
                    # Para imprimir se necesitam el objeto membresía completo
                    membresia_reciente = max(nuevo_socio.membresias, key=lambda m: m.fecha_fin)
                    self._generar_y_abrir_pdf(nuevo_socio, membresia_reciente)

                # Actualizar y limpiar campos independientemente de la respuesta
                self.actualizar_lista()
                self.limpiar_campos()
            else:
                QMessageBox.critical(self, "Error", "No se pudo completar el registro. La base de datos no ha sido modificada.")
                
        except ValueError as e:
            QMessageBox.critical(self, "Error de Datos", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error Inesperado", f"Ocurrió un error inesperado: {e}")
            print(f"Error detallado en registro: {e}")  # Para debugging
    
    def actualizar_lista(self):
        self.tabla_socios.setRowCount(0)
        try:
            socios = self.servicio_socios.obtener_socios_con_membresia()
            for i, socio in enumerate(socios):
                self.tabla_socios.insertRow(i)
                nombre_completo = f"{socio.nombre} {socio.apellido_paterno} {socio.apellido_materno or ''}".strip()
                nombre_plan, estatus, fecha_ini_str, fecha_fin_str = "Sin membresía", "Inactivo", "- - -", "- - -"
                if socio.membresias:
                    membresia_reciente = max(socio.membresias, key=lambda m: m.fecha_fin)
                    nombre_plan = membresia_reciente.plan.nombre
                    fecha_ini_str = membresia_reciente.fecha_inicio.strftime('%Y-%m-%d')
                    fecha_fin_str = membresia_reciente.fecha_fin.strftime('%Y-%m-%d')
                    estatus = self.servicio_membresia.calcular_estatus_membresia(membresia_reciente.fecha_fin)
                
                item_estatus = QTableWidgetItem(estatus)
                # --- LÓGICA DE ESTILO VISUAL ---
                if "Vencido" in estatus or "Inactivo" in estatus:
                    item_estatus.setBackground(QColor(COLOR_VENCIDO))
                    item_estatus.setForeground(QColor("white"))
                elif "Por Vencer" in estatus or "Vence Hoy" in estatus:
                    item_estatus.setBackground(QColor("#FFC107")) 
                    item_estatus.setForeground(QColor("black"))
                elif "Activo" in estatus:
                    item_estatus.setBackground(QColor(COLOR_ACTIVO))
                    item_estatus.setForeground(QColor("white"))
                
                item_estatus.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # --- FIN DE LÓGICA DE ESTILO ---

                self.tabla_socios.setItem(i, 0, QTableWidgetItem(str(socio.id)))
                self.tabla_socios.setItem(i, 1, QTableWidgetItem(nombre_completo))
                self.tabla_socios.setItem(i, 2, QTableWidgetItem(nombre_plan))
                self.tabla_socios.setItem(i, 3, QTableWidgetItem(fecha_ini_str))
                self.tabla_socios.setItem(i, 4, QTableWidgetItem(fecha_fin_str))
                self.tabla_socios.setItem(i, 5, item_estatus)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los socios: {e}")

    def al_seleccionar_tabla(self, item):
        fila = item.row()
        id_socio = self.tabla_socios.item(fila, 0).text()
        socio_obj = self.servicio_socios.obtener_socio_por_id(int(id_socio))
        if socio_obj:
            self.campo_id.setText(str(socio_obj.id))
            self.campo_nombre.setText(socio_obj.nombre)
            self.campo_apellido_paterno.setText(socio_obj.apellido_paterno)
            self.campo_apellido_materno.setText(socio_obj.apellido_materno or "")
            
            # Mostrar foto del socio si existe
            if hasattr(socio_obj, 'foto_ruta') and socio_obj.foto_ruta:
                # Si la foto está almacenada como bytes en la BD
                self.mostrar_foto_socio(socio_obj.foto_ruta)
                # Guardar la foto actual en memoria para posible modificación
                self.foto_actual = socio_obj.foto_ruta
            else:
                self.label_foto.clear()
                self.label_foto.setText("Sin Foto")
                self.foto_actual = None
            # Mostrar estado de huella
            if hasattr(socio_obj, 'huella_template') and socio_obj.huella_template:
                self.mostrar_estado_huella(True)
            else:
                self.mostrar_estado_huella(False)
            if socio_obj.membresias:
                membresia_reciente = max(socio_obj.membresias, key=lambda m: m.fecha_fin)
                plan_nombre = membresia_reciente.plan.nombre
                self.combo_membresia.setCurrentText(plan_nombre)
                # Guardamos el plan original
                self.plan_original_seleccionado = plan_nombre
                self.campo_fecha_ini.setText(membresia_reciente.fecha_inicio.strftime('%Y-%m-%d'))
                self.campo_fecha_fin.setText(membresia_reciente.fecha_fin.strftime('%Y-%m-%d'))
                estatus = self.servicio_membresia.calcular_estatus_membresia(membresia_reciente.fecha_fin)
                self.campo_estatus.setText(estatus)
            else:
                self.limpiar_campos_membresia()
                # Reseteamos el plan original
                self.plan_original_seleccionado = None

        self.btn_registrar.hide()
        self.btn_modificar.show()
        self.btn_eliminar.show()
        self.btn_imprimir.show() 
    
    def modificar_socios(self):
        socio_id_str = self.campo_id.text()
        if not socio_id_str:
            QMessageBox.warning(self, "Error", "Por favor, seleccione un socio de la tabla para modificar.")
            return

        # Verificamos si el usuario cambió la membresía en el ComboBox
        plan_actual_en_combo = self.combo_membresia.currentText()
        hubo_cambio_de_plan = (self.plan_original_seleccionado is not None and
                               plan_actual_en_combo != self.plan_original_seleccionado)

        # Pedimos confirmación al usuario
        respuesta = QMessageBox.question(self, "Confirmar Modificación",
                                         "¿Está seguro de que desea guardar los cambios en los datos personales de este socio?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if respuesta == QMessageBox.StandardButton.Yes:
            nombre = self.campo_nombre.text().strip()
            apellido_paterno = self.campo_apellido_paterno.text().strip()
            apellido_materno = self.campo_apellido_materno.text().strip()
            
            # Validar campos obligatorios
            if not nombre or not apellido_paterno:
                QMessageBox.warning(self, "Error", "El nombre y el apellido paterno no pueden estar vacíos.")
                return
            
            # Validar datos del socio
            es_valido, mensaje = self.validar_datos_socio(nombre, apellido_paterno, apellido_materno)
            if not es_valido:
                QMessageBox.warning(self, "Error de Validación", mensaje)
                return

            try:
                # Determinar qué hacer con la foto
                foto_para_actualizar = None
                
                if self.foto_actual == b'':
                    # Foto marcada para eliminación
                    foto_para_actualizar = b''
                    print("Foto marcada para eliminación")
                elif self.foto_actual is not None and len(self.foto_actual) > 0:
                    # Nueva foto o foto modificada
                    foto_para_actualizar = self.foto_actual
                    print("Foto nueva/modificada")
                else:
                    # Sin cambios en la foto
                    foto_para_actualizar = None
                    print("Sin cambios en la foto")
                
                # Determinar qué hacer con la huella
                huella_para_actualizar = None
                if self.huella_actual == b'':
                    huella_para_actualizar = b''
                    print("Huella marcada para eliminación")
                elif self.huella_actual is not None and len(self.huella_actual) > 0:
                    huella_para_actualizar = self.huella_actual
                    print("Huella nueva/modificada")
                else:
                    huella_para_actualizar = None
                    print("Sin cambios en la huella")

                exito = self.servicio_socios.modificar(
                    socio_id=int(socio_id_str),
                    nombre=nombre,
                    apellido_paterno=apellido_paterno,
                    apellido_materno=apellido_materno,
                    foto_bytes=foto_para_actualizar,
                    huella_template=huella_para_actualizar
                )
            except ValueError as e:
                QMessageBox.critical(self, "Error de Datos", str(e))
                return
            except Exception as e:
                QMessageBox.critical(self, "Error Inesperado", f"Error al modificar socio: {e}")
                return

            if exito:
                # Preparar mensaje de éxito
                mensaje_exito = "Los datos del socio han sido actualizados exitosamente."
                
                # Verificar qué se cambió con la foto
                if foto_para_actualizar == b'':
                    mensaje_exito += "\n\n Foto eliminada."
                elif foto_para_actualizar is not None and len(foto_para_actualizar) > 0:
                    mensaje_exito += "\n\n Foto actualizada."
                # Verificar qué se cambió con la huella
                if huella_para_actualizar == b'':
                    mensaje_exito += "\n\n Huella eliminada."
                elif huella_para_actualizar is not None and len(huella_para_actualizar) > 0:
                    mensaje_exito += "\n\n Huella actualizada."
                
                # Si el usuario intentó cambiar el plan, le mostramos el aviso
                if hubo_cambio_de_plan:
                    mensaje_exito += "\n\n Para renovar o cambiar la membresía, utilice el módulo de Pagos."
                    QMessageBox.information(self, "Aviso", mensaje_exito)
                else:
                    QMessageBox.information(self, "Éxito", mensaje_exito)
                
                self.actualizar_lista()
                
                # Si se eliminó la foto, limpiar el área de foto
                if foto_para_actualizar == b'':
                    self.label_foto.clear()
                    self.label_foto.setText("Sin Foto")
                    self.foto_actual = None
                
                # Volvemos a seleccionar la fila para que los datos actualizados se muestren
                # en el formulario, incluyendo el plan original.
                for fila in range(self.tabla_socios.rowCount()):
                    if self.tabla_socios.item(fila, 0).text() == socio_id_str:
                        self.tabla_socios.setCurrentCell(fila, 0)
                        # Solo recargar datos si no se eliminó la foto
                        if foto_para_actualizar != b'':
                            self.al_seleccionar_tabla(self.tabla_socios.item(fila, 0))
                        break
            else:
                QMessageBox.critical(self, "Error", "No se pudieron actualizar los datos del socio.")

    def eliminar_socios(self):
        """Maneja la solicitud de eliminación de un socio, delegando la lógica de negocio al servicio."""
        id_socio = self.campo_id.text()
        if not id_socio:
            QMessageBox.warning(self, "Error", "Seleccione un socio de la tabla.")
            return

        nombre_socio = f"{self.campo_nombre.text()} {self.campo_apellido_paterno.text()}".strip()

        # Confirmación final del usuario
        respuesta = QMessageBox.question(
            self, "Confirmar Eliminación",
            f"¿Está seguro de que desea eliminar permanentemente al socio:\n\n"
            f"ID: {id_socio}\n"
            f"Nombre: {nombre_socio}\n\n"
            f"Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if respuesta == QMessageBox.StandardButton.No:
            return

        try:
            # La lógica de negocio está ahora en el servicio.
            # El formulario solo llama y maneja la respuesta.
            self.servicio_socios.eliminar(int(id_socio))
            
            QMessageBox.information(
                self, "Éxito",
                f"Socio '{nombre_socio}' eliminado exitosamente."
            )
            self.actualizar_lista()
            self.limpiar_campos()

        except ValueError as e:
            # Captura los errores de negocio
            QMessageBox.warning(self, "Eliminación No Permitida", str(e))
        except Exception as e:
            # Captura otros errores inesperados
            QMessageBox.critical(self, "Error Inesperado", f"Error al eliminar socio: {e}")

    def limpiar_campos(self):
        self.campo_id.clear(); self.campo_nombre.clear()
        self.campo_apellido_paterno.clear(); self.campo_apellido_materno.clear()
        self.limpiar_campos_membresia()
        self.tabla_socios.clearSelection()
        self.btn_registrar.show(); self.btn_modificar.hide(); self.btn_eliminar.hide(); self.btn_imprimir.hide()
        
        self.plan_original_seleccionado = None
        
        # Limpiar foto
        self.foto_actual = None
        self.label_foto.clear()
        self.label_foto.setText("Sin Foto")
        # Limpiar huella
        self.huella_actual = None
        self.mostrar_estado_huella(False)

    def limpiar_campos_membresia(self):
        if self.combo_membresia.count() > 0: self.combo_membresia.setCurrentIndex(0)
        self.campo_fecha_ini.clear(); self.campo_fecha_fin.clear(); self.campo_estatus.clear()

    # ===== MÉTODOS PARA MANEJO DE FOTOS =====
    def tomar_foto(self):
        """Abre la cámara del sistema para capturar foto manualmente"""
        try:
            abrir_camara_sistema() # Llama a la utilidad
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al acceder a la cámara: {e}")
    
    def cargar_foto_archivo(self):
        """Carga una foto desde un archivo"""
        try:
            foto_bytes = cargar_foto_desde_archivo() # Llama a la utilidad
            
            if foto_bytes is not None:
                self.foto_actual = foto_bytes
                
                # Mostrar en el label
                qimage = QImage.fromData(self.foto_actual)
                pixmap = QPixmap.fromImage(qimage)
                # Asegurarse de escalar la imagen para el QLabel
                self.label_foto.setPixmap(pixmap.scaled(self.label_foto.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                self.label_foto.setText("")  # Quitar texto "Sin Foto"
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar la foto: {e}")


    def eliminar_foto(self):
        """Elimina la foto actual"""
        try:
            respuesta = QMessageBox.question(
                self, "Confirmar Eliminación",
                "¿Está seguro de que desea eliminar la foto del socio?\n\n"
                "Esta acción eliminará la foto del socio en la base de datos.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if respuesta == QMessageBox.StandardButton.Yes:
                # Marcar como bytes vacíos para indicar eliminación
                self.foto_actual = b''
                self.label_foto.clear()
                self.label_foto.setText("Sin Foto")
                print("Foto marcada para eliminación (self.foto_actual = b'')")
                QMessageBox.information(self, "Éxito", "Foto eliminada. Recuerde guardar los cambios.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al eliminar la foto: {e}")
    
    # ===== HUELLAS =====
    def mostrar_estado_huella(self, hay_huella: bool, tamano: int | None = None):
        """Actualiza el label de huella para reflejar estado actual."""
        try:
            if hay_huella:
                texto = "Huella capturada"
                if tamano is not None:
                    texto += f" ({tamano} bytes)"
                self.label_huella.setText(texto)
            else:
                self.label_huella.setText("Sin Huella")
        except Exception:
            self.label_huella.setText("Sin Huella")

    def capturar_huella(self):
        """Inicia el proceso de captura de huella utilizando el SDK de DigitalPersona."""
        if self.enrollment_thread and self.enrollment_thread.isRunning():
            QMessageBox.warning(self, "Proceso en Curso", "Ya hay un proceso de captura de huella en ejecución.")
            return

        import platform
        if platform.system().lower() != "windows":
            QMessageBox.information(self, "No compatible", "La captura de huella requiere Windows y el SDK de DigitalPersona instalado.")
            return

        self.enrollment_thread = EnrollmentWorker()
        self.enrollment_thread.proceso_finalizado.connect(self._on_huella_capturada)
        self.enrollment_thread.error_sdk.connect(self._on_error_sdk_huella)
        self.enrollment_thread.estado_actualizado.connect(self._on_estado_huella_actualizado)
        
        # Deshabilitar botones mientras se captura
        self.btn_capturar_huella.setEnabled(False)
        self.btn_eliminar_huella.setEnabled(False)

        self.enrollment_thread.start()
        QMessageBox.information(self, "Captura de Huella", "Se ha iniciado el lector.\n\nPor favor, coloque y levante el dedo 4 veces sobre el sensor siguiendo las instrucciones.")

    def _on_huella_capturada(self, template_bytes, template_size):
        """Slot que se ejecuta cuando el worker emite la señal de proceso finalizado."""
        self.huella_actual = template_bytes
        self.mostrar_estado_huella(True, template_size)
        QMessageBox.information(self, "Éxito", "Huella capturada y procesada correctamente.")
        self._finalizar_proceso_huella()

    def _on_error_sdk_huella(self, mensaje):
        """Slot para manejar errores del SDK."""
        QMessageBox.critical(self, "Error de Lector de Huella", mensaje)
        self._finalizar_proceso_huella()

    def _on_estado_huella_actualizado(self, mensaje):
        """Actualiza la UI con mensajes del proceso de captura."""
        self.label_huella.setText(f"Estado: {mensaje.replace('.', '.\n')}")

    def _finalizar_proceso_huella(self):
        """Limpia y restaura la UI después de la captura."""
        if self.enrollment_thread and self.enrollment_thread.isRunning():
            self.enrollment_thread.stop()
            self.enrollment_thread.wait()
        self.enrollment_thread = None
        self.btn_capturar_huella.setEnabled(True)
        self.btn_eliminar_huella.setEnabled(True)

    def eliminar_huella(self):
        """Marca la huella para eliminación en la siguiente guardada."""
        try:
            respuesta = QMessageBox.question(
                self, "Confirmar Eliminación",
                "¿Está seguro de que desea eliminar la huella del socio?\n\nEsta acción eliminará la huella en la base de datos al guardar.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if respuesta == QMessageBox.StandardButton.Yes:
                self.huella_actual = b''
                self.mostrar_estado_huella(False)
                QMessageBox.information(self, "Éxito", "Huella marcada para eliminación. Recuerde guardar los cambios.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al eliminar la huella: {e}")
    
    def mostrar_foto_socio(self, foto_bytes):
        """Muestra la foto de un socio en el label"""
        try:
            if foto_bytes:
                # Convertir bytes a QPixmap
                qimage = QImage.fromData(foto_bytes)
                pixmap = QPixmap.fromImage(qimage) # No se escala aquí
                # Escalar el pixmap para ajustarse al QLabel
                self.label_foto.setPixmap(pixmap.scaled(self.label_foto.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                self.label_foto.setText("")
            else:
                self.label_foto.clear()
                self.label_foto.setText("Sin Foto")
                
        except Exception as e:
            print(f"Error al mostrar foto: {e}")
            self.label_foto.clear()
            self.label_foto.setText("Error al cargar foto")

    # ===== BÚSQUEDA Y CREDENCIAL =====

    def buscar_socio(self):
        """Busca un socio por nombre y muestra su credencial si lo encuentra."""
        texto_busqueda = self.campo_busqueda.text().strip()
        if not texto_busqueda:
            QMessageBox.information(self, "Búsqueda", "Por favor, ingrese un nombre para buscar.")
            return

        try:
            resultados = self.servicio_socios.buscar_por_nombre_aproximado(texto_busqueda)

            if not resultados:
                QMessageBox.warning(self, "Sin Resultados", f"No se encontró ningún socio que coincida con '{texto_busqueda}'.")
            elif len(resultados) > 1:
                # Si hay múltiples resultados, informamos al usuario para que sea más específico
                nombres = "\n".join([f"- {s.nombre} {s.apellido_paterno}" for s in resultados[:5]])
                QMessageBox.information(self, "Múltiples Coincidencias",
                                        f"Se encontraron varios socios. Por favor, sea más específico.\n\nCoincidencias:\n{nombres}")
            else:
                # Se encontró un único socio.
                socio_encontrado = resultados[0]
                # Creamos y mostramos el diálogo de la credencial
                dialogo = DialogoCredencial(socio_encontrado, self)
                dialogo.exec()

        except Exception as e:
            QMessageBox.critical(self, "Error de Búsqueda", f"Ocurrió un error al buscar: {e}")

    def imprimir_voucher(self):
        """
        Prepara los datos y llama a la función para generar e imprimir el voucher.
        """
        socio_id_str = self.campo_id.text()
        if not socio_id_str:
            QMessageBox.warning(self, "Acción Requerida", "Por favor, seleccione un socio de la tabla para imprimir su comprobante.")
            return

        try:
            socio = self.servicio_socios.obtener_socio_por_id(int(socio_id_str))
            if not socio:
                QMessageBox.critical(self, "Error", "No se encontró el socio seleccionado en la base de datos.")
                return

            if not socio.membresias:
                QMessageBox.information(self, "Sin Membresía", "Este socio no tiene una membresía registrada para generar un comprobante.")
                return
            
            # Usamos la membresía más reciente para el comprobante
            membresia_reciente = max(socio.membresias, key=lambda m: m.fecha_fin)
            
            self._generar_y_abrir_pdf(socio, membresia_reciente)

        except Exception as e:
            QMessageBox.critical(self, "Error Inesperado", f"Ocurrió un error al preparar los datos para la impresión: {e}")

    def _generar_y_abrir_pdf(self, socio, membresia):
        """Función auxiliar para generar y abrir el PDF."""
        import os
        # Crear una carpeta temporal para los vouchers si no existe
        ruta_vouchers = "./vouchers"
        if not os.path.exists(ruta_vouchers):
            os.makedirs(ruta_vouchers)
        
        # Nombre del archivo PDF
        nombre_archivo = f"voucher_socio_{socio.id}_{date.today().strftime('%Y%m%d')}.pdf"
        ruta_completa = os.path.join(ruta_vouchers, nombre_archivo)
        
        exito_gen, error_gen = generar_voucher_socio(socio, membresia, ruta_completa)
        if exito_gen:
            exito_abrir, error_abrir = abrir_archivo(ruta_completa)
            if not exito_abrir:
                QMessageBox.warning(self, "Error al Abrir PDF", error_abrir)
        else:
            QMessageBox.critical(self, "Error al Generar PDF", f"No se pudo crear el comprobante: {error_gen}")