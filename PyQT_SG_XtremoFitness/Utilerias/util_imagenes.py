from PIL import Image
import io
from PyQt6.QtCore import Qt 
from PyQt6.QtGui import QPixmap

def procesar_imagen_para_perfil(ruta_archivo: str, target_size: int = 150) -> bytes:
    """
    Carga una imagen, la recorta en formato cuadrado y la redimensiona.
    Devuelve los bytes de la imagen procesada en formato PNG.

    Args:
        ruta_archivo (str): La ruta al archivo de imagen.
        target_size (int): El tamaño final (ancho y alto) de la imagen.

    Returns:
        bytes: Los datos de la imagen procesada.
    """
    # Cargar imagen con PIL para procesamiento
    imagen_pil = Image.open(ruta_archivo)
    
    # --- Lógica de escalado y recorte (Cover) ---
    original_width, original_height = imagen_pil.size
    if original_width < original_height:
        new_width = target_size
        new_height = int(original_height * (target_size / original_width))
    else:
        new_height = target_size
        new_width = int(original_width * (target_size / original_height))
    imagen_redimensionada = imagen_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Recortar el centro de la imagen para que sea cuadrada
    left = (new_width - target_size) / 2
    top = (new_height - target_size) / 2
    right = (new_width + target_size) / 2
    bottom = (new_height + target_size) / 2
    imagen_cuadrada = imagen_redimensionada.crop((left, top, right, bottom))
    
    buffer = io.BytesIO()
    imagen_cuadrada.save(buffer, format='PNG')
    return buffer.getvalue()

def abrir_imagen_como_pixmap(ruta: str, ancho_max: int, alto_max: int) -> QPixmap:
    """
    Abre una imagen desde una ruta y la devuelve como un QPixmap reescalado.
    """
    pixmap = QPixmap(ruta)
    # Reescalamos la imagen manteniendo la proporción y con un suavizado
    # Usamos Qt.KeepAspectRatio y Qt.SmoothTransformation para calidad y proporción
    pixmap = pixmap.scaled(ancho_max, alto_max, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    return pixmap