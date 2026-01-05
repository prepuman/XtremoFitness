from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFrame, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtCore import Qt

# Reutilizamos la misma capa de servicios
from aplicacion.serviciosPlan import ServiciosPlan
from config import *

class PlanRegistro(QWidget):
    planes_actualizados = pyqtSignal()  # Señal para notificar cambios en los planes
    def __init__(self, master=None):
        super().__init__(master)
        
        self.servicio_planes = ServiciosPlan()
        
        # Crear la interfaz de usuario completa
        self._crear_ui()
        
        # Cargar los datos iniciales en la tabla y configurar botones
        self.actualizar_lista()
        self.limpiar_campos()

    def _crear_ui(self):
        # Layout principal que organiza todo verticalmente
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(20, 20, 20, 20)
        layout_principal.setSpacing(15)
        self.setStyleSheet(f"background-color: {COLOR_FONDO}; color: white; font-size: 14px;")

        # --- Título ---
        label_titulo = QLabel("GESTIÓN DE PLANES")
        label_titulo.setStyleSheet(f"font-size: 24px; font-weight: bold; color: white; background-color: {COLOR_TITULO}; padding: 10px; border-radius: 5px;")
        label_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(label_titulo)

        # --- Formulario de Información (con el nuevo campo) ---
        marco_info = QFrame()
        layout_info = QHBoxLayout(marco_info)
        
        layout_info.addWidget(QLabel("Id:"))
        self.campo_id = QLineEdit(); self.campo_id.setReadOnly(True); self.campo_id.setFixedWidth(50)
        self.campo_id.setStyleSheet("background-color: #333; color: #CCC; border-radius: 4px; padding: 5px;")
        layout_info.addWidget(self.campo_id)
        layout_info.addSpacing(15)

        layout_info.addWidget(QLabel("Plan:")); self.campo_nombre = QLineEdit()
        self.campo_nombre.setStyleSheet("background-color: white; color: black; border-radius: 4px; padding: 5px;"); layout_info.addWidget(self.campo_nombre)
        layout_info.addSpacing(15)

        layout_info.addWidget(QLabel("Precio:")); self.campo_precio = QLineEdit()
        self.campo_precio.setStyleSheet("background-color: white; color: black; border-radius: 4px; padding: 5px;"); layout_info.addWidget(self.campo_precio)
        layout_info.addSpacing(15)
        
        layout_info.addWidget(QLabel("Duración (días):")); self.campo_duracion = QLineEdit()
        self.campo_duracion.setFixedWidth(100)
        self.campo_duracion.setStyleSheet("background-color: white; color: black; border-radius: 4px; padding: 5px;")
        layout_info.addWidget(self.campo_duracion)
        
        layout_principal.addWidget(marco_info)

        # --- Barra de Botones ---
        marco_botones = QFrame(); layout_botones = QHBoxLayout(marco_botones); layout_botones.addStretch()
        self.btn_registrar = QPushButton("Registrar Plan"); self.btn_modificar = QPushButton("Modificar Plan")
        self.btn_eliminar = QPushButton("Eliminar Plan"); self.btn_limpiar = QPushButton("Limpiar Campos")
        
        # Estilos y conexión de botones
        self.btn_registrar.setStyleSheet(f"background-color: {COLOR_BTN_REGISTRAR}; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")
        self.btn_modificar.setStyleSheet(f"background-color: {COLOR_BTN_MODIFICAR}; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")
        self.btn_eliminar.setStyleSheet(f"background-color: {COLOR_BTN_ELIMINAR}; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")
        self.btn_limpiar.setStyleSheet(f"background-color: {COLOR_LIMPIAR_CAMPOS}; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")

        self.btn_registrar.clicked.connect(self.registrar_plan)
        self.btn_modificar.clicked.connect(self.modificar_plan)
        self.btn_eliminar.clicked.connect(self.eliminar_plan)
        self.btn_limpiar.clicked.connect(self.limpiar_campos)
        
        layout_botones.addWidget(self.btn_limpiar); layout_botones.addWidget(self.btn_eliminar)
        layout_botones.addWidget(self.btn_modificar); layout_botones.addWidget(self.btn_registrar)
        layout_principal.addWidget(marco_botones)

        # --- Tabla de Planes (con la nueva columna) ---
        self.tabla_planes = QTableWidget()
        self.tabla_planes.setColumnCount(4)
        self.tabla_planes.setHorizontalHeaderLabels(["ID", "Nombre del Plan", "Precio", "Duración (días)"])
        self.tabla_planes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_planes.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_planes.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_planes.itemClicked.connect(self.al_seleccionar_tabla)
        self.tabla_planes.setStyleSheet(f"""
            QTableWidget {{ background-color: #FFFFFF; color: #000000; gridline-color: #D0D0D0; font-size: 14px; }}
            QHeaderView::section {{ background-color: {COLOR_BARRA_SUPERIOR}; color: white; padding: 4px; border: 1px solid {COLOR_BARRA_SUPERIOR}; font-weight: bold; }}
            QTableWidget::item:selected {{ background-color: {COLOR_MENU_CURSOR_ENCIMA}; color: white; }}
        """)
        layout_principal.addWidget(self.tabla_planes)

    def registrar_plan(self):
        nombre = self.campo_nombre.text(); precio_str = self.campo_precio.text()
        duracion_str = self.campo_duracion.text()
        if not nombre or not precio_str or not duracion_str:
            QMessageBox.warning(self, "Error", "Todos los campos son obligatorios."); return
        try:
            precio = float(precio_str); duracion = int(duracion_str)
        except ValueError:
            QMessageBox.warning(self, "Error", "El precio y la duración deben ser números válidos."); return
        try:
            self.servicio_planes.registrar(nombre, precio, duracion)
            QMessageBox.information(self, "Éxito", "Plan registrado.")
            self.actualizar_lista(); self.limpiar_campos()
            self.planes_actualizados.emit()
        except Exception as e: QMessageBox.critical(self, "Error", f"No se pudo registrar el plan: {e}")

    def actualizar_lista(self):
        self.tabla_planes.setRowCount(0)
        try:
            planes = self.servicio_planes.obtener_planes()
            for i, plan in enumerate(planes):
                self.tabla_planes.insertRow(i)
                self.tabla_planes.setItem(i, 0, QTableWidgetItem(str(plan.id)))
                self.tabla_planes.setItem(i, 1, QTableWidgetItem(plan.nombre))
                self.tabla_planes.setItem(i, 2, QTableWidgetItem(f"${plan.precio:,.2f}"))
                self.tabla_planes.setItem(i, 3, QTableWidgetItem(str(plan.duracion_dias)))
        except Exception as e: QMessageBox.critical(self, "Error", f"No se pudieron cargar los planes: {e}")

    def al_seleccionar_tabla(self, item):
        fila = item.row()
        id_plan = self.tabla_planes.item(fila, 0).text(); nombre = self.tabla_planes.item(fila, 1).text()
        precio = self.tabla_planes.item(fila, 2).text().replace('$', '').replace(',', ''); duracion = self.tabla_planes.item(fila, 3).text()
        
        self.campo_id.setText(id_plan); self.campo_nombre.setText(nombre)
        self.campo_precio.setText(precio); self.campo_duracion.setText(duracion)
        
        self.btn_registrar.hide(); self.btn_modificar.show(); self.btn_eliminar.show()

    def modificar_plan(self):
        id_plan = self.campo_id.text()
        if not id_plan: QMessageBox.warning(self, "Error", "Seleccione un plan de la tabla."); return
        try:
            nombre = self.campo_nombre.text(); precio = float(self.campo_precio.text()); duracion = int(self.campo_duracion.text())
            self.servicio_planes.modificar(int(id_plan), nombre, precio, duracion)
            QMessageBox.information(self, "Éxito", "Plan modificado.")
            self.actualizar_lista()
            self.planes_actualizados.emit()
            self.limpiar_campos()
        except Exception as e: QMessageBox.critical(self, "Error", f"No se pudo modificar el plan: {e}")

    def eliminar_plan(self):
        id_plan = self.campo_id.text()
        if not id_plan:
            QMessageBox.warning(self, "Error de Eliminación", "Por favor, seleccione un plan de la tabla.")
            return
        
        # Pide confirmación al usuario antes de borrar
        respuesta = QMessageBox.question(self, "Confirmar Eliminación",
                                        f"¿Estás seguro de que deseas eliminar el plan con ID {id_plan}?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                # Guardamos el resultado (True o False) que nos devuelve el servicio
                exito = self.servicio_planes.eliminar(int(id_plan))

                if exito:
                    QMessageBox.information(self, "Éxito", "Plan eliminado correctamente.")
                    self.actualizar_lista()
                    self.limpiar_campos()
                    self.planes_actualizados.emit() # Notifica a otros módulos del cambio
                else:
                    QMessageBox.warning(self, "Operación denegada", 
                                        "No se puede eliminar el plan porque está siendo utilizado por uno o más socios.")
            except Exception as e:
                QMessageBox.critical(self, "Error de Eliminación", f"Ocurrió un error inesperado: {e}")
                
    def limpiar_campos(self):
        self.campo_id.clear(); self.campo_nombre.clear()
        self.campo_precio.clear(); self.campo_duracion.clear()
        self.tabla_planes.clearSelection()
        self.btn_registrar.show(); self.btn_modificar.hide(); self.btn_eliminar.hide()