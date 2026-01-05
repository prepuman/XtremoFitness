# Se necesita este import de PyQt6
from PyQt6.QtGui import QGuiApplication

def centrar_ventana(ventana):
    """
    Centra una ventana (QWidget) en la pantalla principal.
    """
    # Obtenemos la geometría de la pantalla principal
    pantalla = QGuiApplication.primaryScreen().geometry()
    
    # Obtenemos la geometría de nuestra ventana
    geometria_ventana = ventana.frameGeometry()
    
    # Movemos el centro de nuestra ventana al centro de la pantalla
    punto_central = pantalla.center()
    geometria_ventana.moveCenter(punto_central)
    
    # Movemos la esquina superior izquierda de la ventana a la nueva posición
    ventana.move(geometria_ventana.topLeft())