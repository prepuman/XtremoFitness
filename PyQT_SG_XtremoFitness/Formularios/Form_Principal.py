import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFrame, QStackedWidget)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QIcon, QPixmap

# --- AÑADIR/MODIFICAR ---
# Importamos la clase de nuestro nuevo módulo de planes
from Formularios.Form_plan import PlanRegistro
from Formularios.Form_socios import SocioRegistro
from Formularios.Form_pagos import PagosRegistro
from Formularios.Form_accesos import AccesoRegistro
from config import *

class Form_Principal(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.ancho_menu_expandido = 220
        self.ancho_menu_colapsado = 60
        self.menu_colapsado = False
        
        self.setWindowTitle("Gestión de Membresías - Xtremo Fitness")
        self.resize(1024, 600)
        self.setWindowIcon(QIcon("./Imagenes/logo.ico"))
        
        self._crear_ui()

    def _crear_ui(self):
        # Carga de Iconos para los botones
        self.icon_inicio = QIcon("./Imagenes/inicio.png") # Sin icono para volver a la bienvenida 
        self.icon_socios = QIcon("./Imagenes/socios.png")
        self.icon_planes = QIcon("./Imagenes/planes.png")
        self.icon_pagos = QIcon("./Imagenes/pagos.png")
        self.icon_accesos = QIcon("./Imagenes/accesos.png")

        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        
        layout_principal = QHBoxLayout(widget_central)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        # --- Menú Lateral ---
        self.menu_lateral = QFrame()
        self.menu_lateral.setFixedWidth(self.ancho_menu_expandido)
        self.menu_lateral.setStyleSheet(f"background-color: {COLOR_MENU_LATERAL};")
        
        layout_menu = QVBoxLayout(self.menu_lateral)
        layout_menu.setContentsMargins(5, 10, 5, 10) # Reducimos márgenes para más espacio
        layout_menu.setSpacing(15)
        layout_menu.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Imagen de perfil
        self.label_perfil = QLabel()
        pixmap_perfil = QPixmap("./Imagenes/logoPerfil.png").scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.label_perfil.setPixmap(pixmap_perfil)
        self.label_perfil.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_menu.addWidget(self.label_perfil)

        # Botones del menú con iconos
        self.btn_inicio = QPushButton("   Inicio")
        self.btn_inicio.setIcon(self.icon_inicio)

        self.btn_socios = QPushButton("   Socios")
        self.btn_socios.setIcon(self.icon_socios)
        
        self.btn_planes = QPushButton("   Planes")
        self.btn_planes.setIcon(self.icon_planes)

        self.btn_pagos = QPushButton("   Pagos")
        self.btn_pagos.setIcon(self.icon_pagos)

        self.btn_accesos = QPushButton("   Accesos")
        self.btn_accesos.setIcon(self.icon_accesos)
        
        self.botones_menu = {
            self.btn_inicio: "   Inicio",
            self.btn_socios: "   Socios",
            self.btn_planes: "   Planes",
            self.btn_pagos: "   Pagos",
            self.btn_accesos: "   Accesos"
        }
        
        estilo_boton_menu = f"""
            QPushButton {{
                color: white;
                background-color: {COLOR_MENU_LATERAL};
                border: none;
                padding: 10px;
                text-align: left;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_MENU_CURSOR_ENCIMA};
            }}
        """
        
        for boton in self.botones_menu.keys():
            boton.setStyleSheet(estilo_boton_menu)
            boton.setIconSize(QSize(28, 28))
            layout_menu.addWidget(boton)

        # --- Cuerpo Principal ---
        self.cuerpo_principal = QFrame()
        layout_cuerpo = QVBoxLayout(self.cuerpo_principal)
        layout_cuerpo.setContentsMargins(0, 0, 0, 0)
        layout_cuerpo.setSpacing(0)

        # --- Barra Superior ---
        barra_superior = QFrame()
        barra_superior.setFixedHeight(50)
        barra_superior.setStyleSheet(f"background-color: {COLOR_BARRA_SUPERIOR}; color: white;")
        layout_barra_superior = QHBoxLayout(barra_superior)
        
        self.btn_toggle_menu = QPushButton("☰")
        self.btn_toggle_menu.setFixedSize(40, 40)
        self.btn_toggle_menu.setStyleSheet("font-size: 20px; border: none;")
        self.btn_toggle_menu.clicked.connect(self.toggle_menu)
        
        layout_barra_superior.addWidget(self.btn_toggle_menu)
        layout_barra_superior.addStretch()

        # --- Contenedor de contenido (QStackedWidget) ---
        self.contenedor_contenido = QStackedWidget()
        
        # Página de bienvenida
        self.pagina_bienvenida = QWidget()
        self.pagina_bienvenida.setStyleSheet(f"background-color: {COLOR_CUERPO_PRINCIPAL};")
        layout_bienvenida = QVBoxLayout(self.pagina_bienvenida)
        layout_bienvenida.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        label_bienvenido = QLabel("Bienvenido")
        label_bienvenido.setStyleSheet("font-size: 34px; color: #AAAAAA;")
        
        label_xtremo = QLabel("Xtremo Fitness")
        label_xtremo.setStyleSheet("font-size: 48px; color: #333333; font-weight: bold;")
        
        layout_bienvenida.addWidget(label_bienvenido)
        layout_bienvenida.addWidget(label_xtremo)
        
        self.contenedor_contenido.addWidget(self.pagina_bienvenida)

        # --- AÑADIR/MODIFICAR ESTA SECCIÓN ---
        # 1. Creamos una instancia de nuestro módulo de planes
        self.modulo_planes = PlanRegistro()
        self.modulo_socios = SocioRegistro()  # Asegúrate de tener esta clase definida en su respectivo archivo
        self.modulo_accesos = AccesoRegistro()
        self.modulo_pagos = PagosRegistro()
        # 2. La añadimos como una "página" más al contenedor
        self.contenedor_contenido.addWidget(self.modulo_planes)
        self.contenedor_contenido.addWidget(self.modulo_socios)  # Añadimos el módulo de socios
        self.contenedor_contenido.addWidget(self.modulo_accesos)
        self.contenedor_contenido.addWidget(self.modulo_pagos)
        # (Aquí añadirías los otros módulos cuando los crees)

        # --- Conexiones entre módulos ---
        # Cuando se realiza un pago, se actualiza la lista de socios en el módulo de socios y pagos.
        self.modulo_pagos.pago_realizado.connect(self.modulo_socios.actualizar_lista)
        self.modulo_pagos.pago_realizado.connect(self.modulo_pagos.actualizar_lista_socios)
        self.modulo_pagos.pago_realizado.connect(self.modulo_accesos._limpiar_formulario)
        # Cuando el módulo de planes emita "planes_actualizados",
        # se ejecutará el método "cargar_planes_en_combobox" del módulo de socios.
        self.modulo_planes.planes_actualizados.connect(self.modulo_socios.cargar_planes_en_combobox)
        
        # 3. Conectamos las señales "clicked" de los botones a sus acciones
        self.btn_inicio.clicked.connect(lambda: self.contenedor_contenido.setCurrentWidget(self.pagina_bienvenida))
        self.btn_planes.clicked.connect(lambda: self.contenedor_contenido.setCurrentWidget(self.modulo_planes))
        self.btn_socios.clicked.connect(lambda: self.contenedor_contenido.setCurrentWidget(self.modulo_socios))
        self.btn_accesos.clicked.connect(lambda: self.contenedor_contenido.setCurrentWidget(self.modulo_accesos))
        self.btn_pagos.clicked.connect(lambda: self.contenedor_contenido.setCurrentWidget(self.modulo_pagos))
        # --- FIN DE LA SECCIÓN ---

        layout_cuerpo.addWidget(barra_superior)
        layout_cuerpo.addWidget(self.contenedor_contenido)
        
        layout_principal.addWidget(self.menu_lateral)
        layout_principal.addWidget(self.cuerpo_principal)

    def toggle_menu(self):
        ancho_actual = self.menu_lateral.width()
        
        if ancho_actual == self.ancho_menu_expandido:
            ancho_final = self.ancho_menu_colapsado
            for boton, texto in self.botones_menu.items():
                boton.setText("")
        else:
            ancho_final = self.ancho_menu_expandido
            for boton, texto in self.botones_menu.items():
                boton.setText(texto)

        self.animacion = QPropertyAnimation(self.menu_lateral, b"minimumWidth")
        self.animacion.setDuration(200)
        self.animacion.setStartValue(ancho_actual)
        self.animacion.setEndValue(ancho_final)
        self.animacion.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animacion.start()

# --- Punto de entrada para la aplicación ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ventana = Form_Principal()
    ventana.show()
    sys.exit(app.exec())