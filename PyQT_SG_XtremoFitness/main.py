import sys
from PyQt6.QtWidgets import QApplication
from Formularios.Form_Principal import Form_Principal

# Este bloque asegura que el código solo se ejecute cuando corres este archivo directamente
if __name__ == '__main__':
    
    # 1. Crear la aplicación (el "motor"). SIEMPRE debe ser lo primero.
    app = QApplication(sys.argv)
    # 2. Ahora que la aplicación existe, creamos nuestra ventana principal.
    ventana_principal = Form_Principal()
    
    # 3. Mostramos la ventana.
    ventana_principal.show()
    
    # 4. Iniciamos el bucle de la aplicación y el programa esperará aquí hasta que cierres la ventana.
    sys.exit(app.exec())