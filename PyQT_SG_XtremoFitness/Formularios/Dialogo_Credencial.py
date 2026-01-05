from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt
from dominio.modelos import SocioModel
from config import *


class DialogoCredencial(QDialog):
    def __init__(self, socio: SocioModel, parent=None):
        super().__init__(parent)
        self.socio = socio

        self.setWindowTitle(f"Credencial - {socio.nombre} {socio.apellido_paterno}")
        self.setFixedSize(600, 300) # Formato horizontal
        self.setModal(True)
        self.setStyleSheet(f"background-color: {COLOR_FONDO_CREDENCIAL};")

        self._crear_ui()

    def _crear_ui(self):
        layout_principal = QVBoxLayout(self); layout_principal.setContentsMargins(10, 10, 10, 10)
        
        marco_credencial = QFrame()
        marco_credencial.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_MARCO_CREDENCIAL};
                border-radius: 10px;
                color: #000000;
            }}
        """)
        layout_principal.addWidget(marco_credencial)

        # Usamos QGridLayout para un control preciso de la posición
        layout_grid = QGridLayout(marco_credencial)
        layout_grid.setContentsMargins(15, 15, 15, 15)
        layout_grid.setSpacing(10)

        # Foto del socio
        label_foto = QLabel()
        label_foto.setFixedSize(150, 150)
        label_foto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_foto.setStyleSheet("background-color: #E0E0E0; border: 3px solid #CCCCCC; border-radius: 5px;")
        
        if self.socio.foto_ruta:
            qimage = QImage.fromData(self.socio.foto_ruta)
            pixmap = QPixmap.fromImage(qimage)
            label_foto.setPixmap(pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            label_foto.setText("Sin Foto")
        
        # Añadimos la foto a la izquierda, ocupando 3 filas
        layout_grid.addWidget(label_foto, 0, 0, 3, 1)

        # Datos del socio (Nombre e ID)
        nombre_completo = f"{self.socio.nombre} {self.socio.apellido_paterno} {self.socio.apellido_materno or ''}".strip()
        label_nombre = QLabel(nombre_completo)
        label_nombre.setStyleSheet("font-size: 24px; font-weight: bold; color: #decece;")
        label_nombre.setWordWrap(True)
        label_id = QLabel(f"ID de Socio: {self.socio.id:05d}")
        label_id.setStyleSheet("font-size: 14px; color: #666666; font-weight: bold;")

        layout_grid.addWidget(label_nombre, 0, 1, 1, 2) # Fila 0, Columna 1, ocupa 1 fila y 2 columnas
        layout_grid.addWidget(label_id, 1, 1, 1, 2)     # Fila 1, Columna 1, ocupa 1 fila y 2 columnas

        # Datos de Membresía
        marco_membresia = QFrame()
        marco_membresia.setStyleSheet(f"background-color: {COLOR_DATOS_MEMBRESIA}; border-radius: 5px; padding: 5px;")
        layout_membresia = QGridLayout(marco_membresia)
        layout_membresia.setSpacing(4)

        if self.socio.membresias:
            membresia_reciente = max(self.socio.membresias, key=lambda m: m.fecha_fin)
            from datetime import date
            dias_restantes = (membresia_reciente.fecha_fin - date.today()).days
            estatus, color_estatus, dias_restantes_str = ("VENCIDO", COLOR_VENCIDO, "Vencido") if dias_restantes < 0 else ("ACTIVO", COLOR_ACTIVO, f"{dias_restantes} días")
            
            label_estatus = QLabel(estatus); label_estatus.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label_estatus.setStyleSheet(f"font-size: 16px; font-weight: bold; color: white; background-color: {color_estatus}; padding: 4px; border-radius: 4px;")
            label_plan = QLabel(f"Plan: {membresia_reciente.plan.nombre}"); label_plan.setStyleSheet("font-size: 14px; font-weight: bold;")
            
            label_inicio_titulo = QLabel("Inicio:"); label_inicio_titulo.setStyleSheet("font-weight: bold;")
            label_inicio_valor = QLabel(f"{membresia_reciente.fecha_inicio.strftime('%d/%b/%Y')}")
            label_vence_titulo = QLabel("Vence:"); label_vence_titulo.setStyleSheet("font-weight: bold;")
            label_vence_valor = QLabel(f"{membresia_reciente.fecha_fin.strftime('%d/%b/%Y')}")
            label_restan_titulo = QLabel("Restan:"); label_restan_titulo.setStyleSheet("font-weight: bold;")
            label_restan_valor = QLabel(dias_restantes_str)

            layout_membresia.addWidget(label_estatus, 0, 0, 1, 2)
            layout_membresia.addWidget(label_plan, 1, 0, 1, 2)
            layout_membresia.addWidget(label_inicio_titulo, 2, 0); layout_membresia.addWidget(label_inicio_valor, 2, 1)
            layout_membresia.addWidget(label_vence_titulo, 3, 0); layout_membresia.addWidget(label_vence_valor, 3, 1)
            layout_membresia.addWidget(label_restan_titulo, 4, 0); layout_membresia.addWidget(label_restan_valor, 4, 1)
        else:
            label_sin_membresia = QLabel("Sin Membresía Activa"); label_sin_membresia.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label_sin_membresia.setStyleSheet("font-size: 14px; font-weight: bold; color: #D32F2F;")
            layout_membresia.addWidget(label_sin_membresia)

        # Añadimos el marco de membresía debajo del nombre/id
        layout_grid.addWidget(marco_membresia, 2, 1, 1, 1)

        # Código QR
        label_qr = QLabel()
        label_qr.setFixedSize(100, 100)
        label_qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_qr.setStyleSheet("background-color: white; border: 1px solid #CCCCCC; border-radius: 4px;")
        
        if self.socio.qr_code:
            qimage_qr = QImage.fromData(self.socio.qr_code)
            pixmap_qr = QPixmap.fromImage(qimage_qr)
            label_qr.setPixmap(pixmap_qr.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            label_qr.setText("Sin QR")
        
        # Añadimos el QR a la derecha del marco de membresía, alineado arriba
        layout_grid.addWidget(label_qr, 2, 2, Qt.AlignmentFlag.AlignTop)