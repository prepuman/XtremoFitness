import subprocess
import platform
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtCore import Qt 
from PyQt6.QtGui import QPixmap, QImage

from Utilerias.util_imagenes import procesar_imagen_para_perfil

def abrir_camara_sistema() -> bool:
    """
    Intenta abrir la aplicación de cámara del sistema operativo.
    Devuelve True si se intentó abrir, False si no es compatible o falló.
    """
    sistema = platform.system().lower()
    
    if sistema == "windows":
        try:
            subprocess.run(['start', 'microsoft.windows.camera:'], shell=True, check=True)
            QMessageBox.information(
                None, "Captura de Foto", 
                "La aplicación de cámara se ha abierto.\n\n"
                "1. Tome la foto en la aplicación de cámara\n"
                "2. Guarde la foto en su computadora\n"
                "3. Use el botón '📁' para seleccionar la foto guardada\n\n"
                "Consejo: Guarde la foto en una ubicación fácil de encontrar"
            )
            return True
        except Exception:
            QMessageBox.information(
                None, "Cámara No Disponible", 
                "No se pudo abrir la cámara automáticamente.\n\n"
                "Use el botón '📁' para seleccionar una foto existente."
            )
            return False
    else:
        QMessageBox.information(
            None, "Cámara No Disponible", 
            "La función de abrir la cámara automáticamente solo está disponible en Windows."
        )
        return False

def cargar_foto_desde_archivo() -> bytes | None:
    """
    Abre un diálogo de archivo para que el usuario seleccione una imagen,
    la procesa y devuelve los bytes de la imagen procesada.
    Devuelve None si el usuario cancela o hay un error.
    """
    archivo, _ = QFileDialog.getOpenFileName(
        None, # Parent es None para que el diálogo sea modal a la aplicación
        "Seleccionar Foto del Socio",
        "",
        "Imágenes (*.jpg *.jpeg *.png *.bmp *.gif);;Todos los archivos (*)"
    )
    
    if archivo:
        try:
            foto_bytes = procesar_imagen_para_perfil(archivo)
            QMessageBox.information(None, "Éxito", "Foto cargada correctamente.")
            return foto_bytes
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Error al cargar la foto: {e}")
            return None
    return None

def obtener_pixmap_desde_bytes(foto_bytes: bytes, size: tuple[int, int]) -> QPixmap:
    """Convierte bytes de imagen a QPixmap y la escala."""
    qimage = QImage.fromData(foto_bytes)
    pixmap = QPixmap.fromImage(qimage)
    return pixmap.scaled(size[0], size[1], Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)