from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QComboBox, QGridLayout)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, pyqtSignal
from datetime import date

from aplicacion.serviciosSocio import ServiciosSocio
from aplicacion.serviciosPlan import ServiciosPlan
from aplicacion.serviciosMembresia import ServiciosMembresia
from config import *

class PagosRegistro(QWidget):
    # Señal que se emitirá cuando se complete un pago/renovación
    pago_realizado = pyqtSignal()

    def __init__(self, master=None):
        super().__init__(master)

        self.servicio_socios = ServiciosSocio()
        self.servicio_planes = ServiciosPlan()
        self.servicio_membresia = ServiciosMembresia()

        self._crear_ui()
        self._conectar_senales()

        self.cargar_planes_en_combobox()
        self.actualizar_lista_socios()

    def showEvent(self, event):
        """Se ejecuta cada vez que el widget se hace visible para recargar los datos."""
        super().showEvent(event)
        self.actualizar_lista_socios()
        self.limpiar_seccion_renovacion()

    def _crear_ui(self):
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(20, 20, 20, 20)
        layout_principal.setSpacing(15)
        self.setStyleSheet(f"background-color: {COLOR_FONDO}; color: white; font-size: 14px;")

        # --- Título ---
        label_titulo = QLabel("GESTIÓN DE PAGOS Y RENOVACIONES")
        label_titulo.setStyleSheet(f"font-size: 24px; font-weight: bold; color: white; background-color: {COLOR_TITULO}; padding: 10px; border-radius: 5px;")
        label_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(label_titulo)

        # --- Sección Superior: Filtros y Renovación ---
        layout_superior = QHBoxLayout()
        layout_principal.addLayout(layout_superior)

        # --- Panel de Filtros ---
        frame_filtros = QFrame()
        frame_filtros.setStyleSheet("background-color: #2A2A2A; border-radius: 5px;")
        layout_filtros = QVBoxLayout(frame_filtros)
        layout_filtros.setContentsMargins(15, 15, 15, 15)
        
        label_filtrar = QLabel("Filtrar Socios Por:")
        label_filtrar.setStyleSheet("font-weight: bold;")
        self.combo_filtro = QComboBox()
        self.combo_filtro.addItems(["Todos", "Activos", "Por Vencer", "Vencidos"])
        self.combo_filtro.setStyleSheet("background-color: white; color: black; border-radius: 4px; padding: 5px;")
        
        layout_filtros.addWidget(label_filtrar)
        layout_filtros.addWidget(self.combo_filtro)
        layout_filtros.addStretch()
        layout_superior.addWidget(frame_filtros, 1)

        # --- Panel de Renovación ---
        frame_renovacion = QFrame()
        frame_renovacion.setStyleSheet("background-color: #2A2A2A; border-radius: 5px;")
        layout_renovacion = QGridLayout(frame_renovacion)
        layout_renovacion.setContentsMargins(15, 15, 15, 15)
        
        self.label_socio_seleccionado = QLabel("Socio: (Ninguno seleccionado)")
        self.label_socio_seleccionado.setStyleSheet("font-weight: bold; font-size: 16px;")
        
        self.combo_nuevo_plan = QComboBox()
        self.combo_nuevo_plan.setStyleSheet("background-color: white; color: black; border-radius: 4px; padding: 5px;")
        
        self.label_fecha_inicio = QLabel(f"Fecha de Inicio: {date.today().strftime('%d/%m/%Y')}")
        
        self.btn_confirmar_renovacion = QPushButton("Confirmar Renovación")
        self.btn_confirmar_renovacion.setStyleSheet(f"background-color: {COLOR_BTN_PAGOS}; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")
        self.btn_confirmar_renovacion.setEnabled(False)

        layout_renovacion.addWidget(self.label_socio_seleccionado, 0, 0, 1, 2)
        layout_renovacion.addWidget(QLabel("Nuevo Plan:"), 1, 0)
        layout_renovacion.addWidget(self.combo_nuevo_plan, 1, 1)
        layout_renovacion.addWidget(self.label_fecha_inicio, 2, 0, 1, 2)
        layout_renovacion.addWidget(self.btn_confirmar_renovacion, 3, 0, 1, 2)
        layout_superior.addWidget(frame_renovacion, 3)

        # --- Tabla de Socios ---
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
        self.tabla_socios.setColumnHidden(0, True) # Ocultar ID
        layout_principal.addWidget(self.tabla_socios)

        # Variable para guardar el ID del socio seleccionado
        self.socio_id_seleccionado = None

    def _conectar_senales(self):
        self.combo_filtro.currentTextChanged.connect(self.actualizar_lista_socios)
        self.tabla_socios.itemClicked.connect(self.al_seleccionar_socio)
        self.btn_confirmar_renovacion.clicked.connect(self.renovar_membresia)

    def cargar_planes_en_combobox(self):
        """Carga los planes disponibles en el combobox de renovación."""
        try:
            self.combo_nuevo_plan.clear()
            planes = self.servicio_planes.obtener_planes()
            if planes:
                for plan in planes:
                    self.combo_nuevo_plan.addItem(plan.nombre, userData=plan.id)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los planes para renovación: {e}")

    def actualizar_lista_socios(self):
        """Filtra y actualiza la tabla de socios según el criterio seleccionado."""
        filtro = self.combo_filtro.currentText()
        self.tabla_socios.setRowCount(0)
        try:
            socios = self.servicio_socios.obtener_socios_con_membresia()
            socios_filtrados = []

            for socio in socios:
                estatus = "Inactivo"
                if socio.membresias:
                    membresia_reciente = max(socio.membresias, key=lambda m: m.fecha_fin)
                    estatus = self.servicio_membresia.calcular_estatus_membresia(membresia_reciente.fecha_fin)

                if filtro == "Todos":
                    socios_filtrados.append(socio)
                elif filtro == "Activos" and estatus == "Activo":
                    socios_filtrados.append(socio)
                elif filtro == "Por Vencer" and ("Por Vencer" in estatus or estatus == "Vence Hoy"):
                    socios_filtrados.append(socio)
                elif filtro == "Vencidos" and (estatus == "Vencido" or estatus == "Inactivo"):
                    socios_filtrados.append(socio)

            for i, socio in enumerate(socios_filtrados):
                self.tabla_socios.insertRow(i)
                nombre_completo = f"{socio.nombre} {socio.apellido_paterno} {socio.apellido_materno or ''}".strip()
                nombre_plan, estatus_display, fecha_ini_str, fecha_fin_str = "Sin membresía", "Inactivo", "- - -", "- - -"
                
                if socio.membresias:
                    membresia_reciente = max(socio.membresias, key=lambda m: m.fecha_fin)
                    nombre_plan = membresia_reciente.plan.nombre
                    fecha_ini_str = membresia_reciente.fecha_inicio.strftime('%Y-%m-%d')
                    fecha_fin_str = membresia_reciente.fecha_fin.strftime('%Y-%m-%d')
                    estatus_display = self.servicio_membresia.calcular_estatus_membresia(membresia_reciente.fecha_fin)
                
                item_estatus = QTableWidgetItem(estatus_display)
                # --- LÓGICA DE ESTILO VISUAL ---
                if "Vencido" in estatus_display or "Inactivo" in estatus_display:
                    item_estatus.setBackground(QColor(COLOR_VENCIDO))
                    item_estatus.setForeground(QColor("white"))
                elif "Por Vencer" in estatus_display or "Vence Hoy" in estatus_display:
                    item_estatus.setBackground(QColor("#FFC107")) # Un color ámbar
                    item_estatus.setForeground(QColor("black"))
                elif "Activo" in estatus_display:
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

    def al_seleccionar_socio(self, item):
        """Se activa al hacer clic en un socio de la tabla."""
        if not item:
            return
        
        fila = item.row()
        self.socio_id_seleccionado = int(self.tabla_socios.item(fila, 0).text())
        nombre_socio = self.tabla_socios.item(fila, 1).text()

        self.label_socio_seleccionado.setText(f"Socio: {nombre_socio}")
        self.btn_confirmar_renovacion.setEnabled(True)

    def limpiar_seccion_renovacion(self):
        """Limpia los campos de la sección de renovación."""
        self.socio_id_seleccionado = None
        self.label_socio_seleccionado.setText("Socio: (Ninguno seleccionado)")
        if self.combo_nuevo_plan.count() > 0:
            self.combo_nuevo_plan.setCurrentIndex(0)
        self.btn_confirmar_renovacion.setEnabled(False)
        self.tabla_socios.clearSelection()

    def renovar_membresia(self):
        """Lógica para confirmar y procesar la renovación de una membresía."""
        if self.socio_id_seleccionado is None:
            QMessageBox.warning(self, "Acción Requerida", "Por favor, seleccione un socio de la tabla para renovar.")
            return

        plan_id_seleccionado = self.combo_nuevo_plan.currentData()
        plan_nombre_seleccionado = self.combo_nuevo_plan.currentText()

        if plan_id_seleccionado is None:
            QMessageBox.warning(self, "Acción Requerida", "Por favor, seleccione un nuevo plan para la renovación.")
            return

        # Confirmación del usuario
        socio_nombre = self.label_socio_seleccionado.text().replace("Socio: ", "")
        respuesta = QMessageBox.question(
            self, "Confirmar Renovación",
            f"¿Está seguro de que desea renovar la membresía para:\n\n"
            f"Socio: {socio_nombre}\n"
            f"Nuevo Plan: {plan_nombre_seleccionado}\n\n"
            f"Se creará una nueva membresía a partir de hoy.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if respuesta == QMessageBox.StandardButton.No:
            return

        try:
            # --- INICIO DE LA LÓGICA DE VALIDACIÓN ---
            # Obtener el socio completo para revisar su membresía actual
            socio_obj = self.servicio_socios.obtener_socio_por_id(self.socio_id_seleccionado)
            if not socio_obj:
                QMessageBox.critical(self, "Error", "El socio seleccionado ya no existe.")
                self.actualizar_lista_socios()
                return

            # Validar si el socio puede renovar basado en su estatus actual
            if socio_obj.membresias:
                membresia_reciente = max(socio_obj.membresias, key=lambda m: m.fecha_fin)
                estatus = self.servicio_membresia.calcular_estatus_membresia(membresia_reciente.fecha_fin)
                
                # Regla de negocio: No permitir renovar si la membresía está activa y no está próxima a vencer
                if estatus == "Activo":
                    dias_restantes = (membresia_reciente.fecha_fin - date.today()).days
                    if dias_restantes > 3: # Umbral de 3 días para poder renovar
                        QMessageBox.warning(self, "Renovación No Permitida",
                                            f"El socio ya tiene una membresía activa con {dias_restantes} días restantes.\n\n"
                                            f"Solo se pueden renovar membresías vencidas o que estén a 3 días o menos de vencer.")
                        return
            
            # --- FIN DE LA LÓGICA DE VALIDACIÓN ---


            # Obtener el objeto Plan completo
            plan_obj = self.servicio_planes.obtener_plan_por_id(plan_id_seleccionado)
            if not plan_obj:
                QMessageBox.critical(self, "Error", "El plan seleccionado ya no existe.")
                self.cargar_planes_en_combobox() # Recargar por si fue eliminado
                return

            # Llamar al servicio para registrar la nueva membresía
            nueva_membresia = self.servicio_membresia.renovar_membresia(
                socio_id=self.socio_id_seleccionado,
                plan_id=plan_obj.id
            )

            if nueva_membresia:
                QMessageBox.information(
                    self, "Éxito",
                    f"¡Renovación exitosa!\n\n"
                    f"La nueva membresía para {socio_nombre} es válida hasta el "
                    f"{nueva_membresia.fecha_fin.strftime('%d de %B de %Y')}."
                )
                
                # --- EMITIR SEÑAL ---
                # Notifica a otros módulos (como Form_Principal) que algo cambió.
                self.pago_realizado.emit()

                # Actualizar la vista actual
                self.actualizar_lista_socios()
                self.limpiar_seccion_renovacion()
            else:
                QMessageBox.critical(self, "Error", "No se pudo completar la renovación.")

        except ValueError as ve:
            QMessageBox.warning(self, "Error de Validación", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Error Inesperado", f"Ocurrió un error al renovar la membresía: {e}")