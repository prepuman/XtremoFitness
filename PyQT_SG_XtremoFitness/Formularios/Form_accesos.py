from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFrame, QMessageBox, QComboBox, QPushButton)
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPainterPath
from PyQt6.QtCore import Qt, QUrl, QThread, pyqtSignal
from PyQt6.QtMultimedia import QSoundEffect

import platform
# --- NUEVAS IMPORTACIONES ---
import cv2
from pyzbar.pyzbar import decode
import time
# --- NUEVA IMPORTACIÓN PARA DETECCIÓN RÁPIDA DE CÁMARAS ---
try:
    from pygrabber.dshow_graph import FilterGraph
    PYGRABBER_AVAILABLE = True
except ImportError:
    PYGRABBER_AVAILABLE = False

from config import *
from aplicacion.serviciosSocio import ServiciosSocio
from Utilerias.captura_huella import IdentificationWorker
from datetime import date

# --- NUEVA CLASE: WORKER PARA LA CÁMARA Y QR ---
class CameraWorker(QThread):
    """
    Hilo para manejar la captura de la cámara y la detección de QR sin bloquear la UI.
    """
    # Señal que emite el fotograma actual como una QImage
    frame_actualizado = pyqtSignal(QImage)
    # Señal que emite el dato del QR detectado
    qr_detectado = pyqtSignal(str)
    # Señal para actualizar el estado en la UI
    estado_camara = pyqtSignal(str)

    def __init__(self, camera_index):
        super().__init__()
        self.camera_index = camera_index
        self._is_running = False
        self.last_qr_time = 0
        self.cooldown = 3 # 3 segundos de espera entre detecciones del mismo QR

    def run(self):
        self._is_running = True
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            self.estado_camara.emit(f"Error: No se pudo abrir la cámara {self.camera_index}")
            return

        self.estado_camara.emit("Cámara activa. Buscando QR...")
        while self._is_running:
            ret, frame = cap.read()
            if ret:
                # Convertir el fotograma de OpenCV (BGR) a RGB
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                self.frame_actualizado.emit(qt_image)

                # Decodificar QR
                qrs = decode(frame)
                if qrs and (time.time() - self.last_qr_time > self.cooldown):
                    qr_data = qrs[0].data.decode('utf-8')
                    self.qr_detectado.emit(qr_data)
                    self.last_qr_time = time.time() # Reiniciar temporizador

        cap.release()
        self.estado_camara.emit("Cámara detenida.")

    def stop(self):
        self._is_running = False

# --- NUEVA CLASE: WORKER PARA DESCUBRIR CÁMARAS ---
class CameraDiscoveryWorker(QThread):
    """
    Hilo para descubrir cámaras disponibles sin bloquear la UI.
    """
    camaras_encontradas = pyqtSignal(list)

    def run(self):
        """
        Detecta cámaras. Usa pygrabber para una detección instantánea en Windows.
        Si falla, vuelve al método lento de sondeo como respaldo.
        """
        if platform.system() == "Windows" and PYGRABBER_AVAILABLE:
            try:
                graph = FilterGraph()
                # Obtiene una lista de tuplas (nombre_camara, indice)
                devices = graph.get_input_devices(as_dict=True)
                self.camaras_encontradas.emit(list(devices.items()))
                return
            except Exception:
                # Si pygrabber falla, usamos el método antiguo
                pass
        
        # --- Método de respaldo (lento) ---
        self._sondear_camaras_manualmente()

    def _sondear_camaras_manualmente(self):
        camaras = []
        for i in range(5): # Probar los primeros 5 índices
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                # Para el método manual, no tenemos nombres, solo índices
                camaras.append((f"Cámara {i}", i))
                cap.release()
        self.camaras_encontradas.emit(camaras)


class AccesoRegistro(QWidget):
    def __init__(self, master=None):
        super().__init__(master)
        
        self._crear_ui()
        self._conectar_senales()
        
        # Lógica Adicional
        self.servicios_socio = ServiciosSocio()
        self.identification_thread = None
        # --- NUEVO: Hilo para la cámara ---
        self.camera_thread = None
        # --- NUEVO: Hilo para descubrir cámaras ---
        self.discovery_thread = None
        self._cargar_sonidos()

    def showEvent(self, event):
        """Se ejecuta cada vez que el widget se hace visible."""
        super().showEvent(event)
        self._limpiar_formulario()
        self._iniciar_identificacion_por_huella()
        # --- MODIFICADO: Iniciar búsqueda de cámaras en segundo plano ---
        self._iniciar_busqueda_camaras()

    def hideEvent(self, event):
        """Se ejecuta cada vez que el widget se oculta."""
        self._detener_identificacion_por_huella()
        # --- NUEVO: Detener cámara al ocultar ---
        self._detener_camara()
        self._detener_busqueda_camaras()
        super().hideEvent(event)

    def closeEvent(self, event):
        """Asegura que el hilo se detenga al cerrar la ventana principal."""
        self._detener_identificacion_por_huella()
        self._detener_busqueda_camaras()
        # --- NUEVO: Detener cámara al cerrar ---
        self._detener_camara()
        super().closeEvent(event)

    def _cargar_sonidos(self):
        """Carga los archivos de sonido para éxito y error."""
        self.sonido_exito = QSoundEffect()
        self.sonido_exito.setSource(QUrl.fromLocalFile("./Sonidos/acceso_correcto.wav"))
        self.sonido_exito.setVolume(0.5)

        self.sonido_error = QSoundEffect()
        self.sonido_error.setSource(QUrl.fromLocalFile("./Sonidos/acceso_denegado.wav"))
        self.sonido_error.setVolume(0.5)

    def _crear_ui(self):
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(20, 20, 20, 20)
        layout_principal.setSpacing(15)
        self.setStyleSheet(f"background-color: {COLOR_FONDO}; color: white; font-size: 14px;")

        label_titulo = QLabel("GESTIÓN DE ACCESOS")
        label_titulo.setStyleSheet(f"font-size: 24px; font-weight: bold; color: white; background-color: {COLOR_TITULO}; padding: 10px; border-radius: 5px;")
        label_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(label_titulo)

        # Layout horizontal para dividir la pantalla
        layout_horizontal = QHBoxLayout()
        layout_principal.addLayout(layout_horizontal)

        # --- Lado Izquierdo: Credencial ---
        frame_credencial = QFrame()
        frame_credencial.setStyleSheet(f"background-color: {COLOR_FONDO}; border-radius: 10px;")
        layout_horizontal.addWidget(frame_credencial, 1) # Ocupa 1/3 de la pantalla

        layout_credencial = QVBoxLayout(frame_credencial)
        layout_credencial.setContentsMargins(20, 20, 20, 20)
        layout_credencial.setSpacing(15)
        layout_credencial.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.label_foto = QLabel("Foto")
        self.label_foto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_foto.setFixedSize(150, 150)
        self.label_foto.setStyleSheet("background-color: #333; border: 3px solid #555; border-radius: 75px; color: #AAA;")
        layout_credencial.addWidget(self.label_foto, 0, Qt.AlignmentFlag.AlignCenter)

        self.label_nombre = QLabel("Nombre del Socio")
        self.label_nombre.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        self.label_nombre.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_credencial.addWidget(self.label_nombre)

        self.label_socio_id = QLabel("ID de Socio: N/A")
        self.label_socio_id.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_credencial.addWidget(self.label_socio_id)
        
        self.label_plan = QLabel("Plan: N/A")
        self.label_plan.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_credencial.addWidget(self.label_plan)

        # --- Nuevos labels para detalles de membresía ---
        layout_credencial.addSpacing(20) # Espacio antes de los detalles

        self.label_fecha_inicio = QLabel("Inicio: --/--/----")
        self.label_fecha_inicio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_credencial.addWidget(self.label_fecha_inicio)

        self.label_fecha_fin = QLabel("Fin: --/--/----")
        self.label_fecha_fin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_credencial.addWidget(self.label_fecha_fin)

        self.label_dias_restantes = QLabel("Días restantes: N/A")
        self.label_dias_restantes.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        self.label_dias_restantes.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_credencial.addWidget(self.label_dias_restantes)

        # --- Lado Derecho: Formulario de Acceso ---
        frame_acceso = QFrame()
        frame_acceso.setStyleSheet(f"background-color: {COLOR_FONDO}; border-radius: 10px;")
        layout_horizontal.addWidget(frame_acceso, 2) # Ocupa 2/3 de la pantalla

        layout_acceso = QVBoxLayout(frame_acceso)
        layout_acceso.setContentsMargins(30, 30, 30, 30)
        layout_acceso.setSpacing(20)
        layout_acceso.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- NUEVO: Controles de la cámara ---
        frame_controles_cam = QFrame()
        layout_controles_cam = QHBoxLayout(frame_controles_cam)
        layout_controles_cam.setContentsMargins(0,0,0,0)
        
        self.combo_camaras = QComboBox()
        self.combo_camaras.setStyleSheet("background-color: white; color: black; border-radius: 4px; padding: 5px;")
        self.btn_iniciar_camara = QPushButton("Iniciar/Detener Cámara")
        self.btn_iniciar_camara.setStyleSheet(f"background-color: {COLOR_BOTON}; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")

        layout_controles_cam.addWidget(QLabel("Seleccionar Cámara:"))
        layout_controles_cam.addWidget(self.combo_camaras, 1)
        layout_controles_cam.addWidget(self.btn_iniciar_camara)
        layout_acceso.addWidget(frame_controles_cam)

        # --- NUEVO: Widget para mostrar el video ---
        self.label_video = QLabel("El video de la cámara aparecerá aquí.")
        self.label_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_video.setStyleSheet("background-color: #000; border: 1px solid #555; border-radius: 5px; color: #AAA;")
        self.label_video.setMinimumHeight(240) # Altura mínima para el video
        layout_acceso.addWidget(self.label_video, 1) # El '1' le da más espacio vertical
        
        self.label_estado = QLabel("Esperando...")
        self.label_estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_estado.setStyleSheet("font-size: 22px; font-weight: bold; padding: 20px; border-radius: 10px; color: white;")
        layout_acceso.addWidget(self.label_estado, 1, Qt.AlignmentFlag.AlignCenter)
        
        # --- NUEVO: Label para estado del lector de huella ---
        self.label_estado_huella = QLabel("Inicializando lector de huella...")
        self.label_estado_huella.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_estado_huella.setStyleSheet("font-size: 12px; color: #AAAAAA; font-style: italic;")
        layout_acceso.addWidget(self.label_estado_huella)

    def _conectar_senales(self):
        # --- NUEVO: Conectar botón de la cámara ---
        self.btn_iniciar_camara.clicked.connect(self._toggle_camara)
    
    def _actualizar_estado(self, mensaje, color=None):
        self.label_estado.setText(mensaje)
        self.label_estado.setStyleSheet(f"background-color: {color or 'transparent'}; color: white; font-size: 22px; font-weight: bold; padding: 20px; border-radius: 10px;")
        
        if color == COLOR_EXITO: self.sonido_exito.play()
        elif color == COLOR_ERROR: self.sonido_error.play()

    def _actualizar_credencial(self, socio):
        # --- Foto Circular ---
        if socio.foto_ruta:
            qimage = QImage.fromData(socio.foto_ruta)
            pixmap_original = QPixmap.fromImage(qimage)
            pixmap_circular = self._crear_pixmap_circular(pixmap_original, 150)
            self.label_foto.setPixmap(pixmap_circular)
        else:
            self.label_foto.setText("Sin Foto")
            self.label_foto.setStyleSheet("background-color: #333; border: 3px solid #555; border-radius: 75px; color: #AAA;")

        # Actualizar datos
        self.label_nombre.setText(f"{socio.nombre} {socio.apellido_paterno}")
        self.label_socio_id.setText(f"ID de Socio: {socio.id}")

        # Lógica para verificar la membresía
        hoy = date.today()
        
        # --- LÓGICA CORREGIDA ---
        # En lugar de tomar la primera membresía activa que encuentre, buscamos la más reciente.
        # Esto soluciona el bug donde se mostraba una membresía antigua si se renovaba el mismo día.
        if socio.membresias:
            membresia_reciente = max(socio.membresias, key=lambda m: m.fecha_fin)
        else:
            membresia_reciente = None

        # Verificamos si la membresía más reciente está activa hoy
        if membresia_reciente and membresia_reciente.fecha_inicio <= hoy <= membresia_reciente.fecha_fin:
            self.label_plan.setText(f"Plan: {membresia_reciente.plan.nombre}")
            self._actualizar_estado("ACCESO CORRECTO", COLOR_EXITO)
            
            # Actualizar nuevos labels
            self.label_fecha_inicio.setText(f"Inicio: {membresia_reciente.fecha_inicio.strftime('%d/%m/%Y')}")
            self.label_fecha_fin.setText(f"Fin: {membresia_reciente.fecha_fin.strftime('%d/%m/%Y')}")
            dias_restantes = (membresia_reciente.fecha_fin - hoy).days
            self.label_dias_restantes.setText(f"Quedan {dias_restantes} días")
        else:
            self.label_plan.setText("Plan: N/A")
            self._actualizar_estado("ACCESO DENEGADO", COLOR_ERROR)
            
            # Limpiar nuevos labels
            self.label_fecha_inicio.setText("Inicio: --/--/----")
            self.label_fecha_fin.setText("Fin: --/--/----")
            self.label_dias_restantes.setText("Membresía no activa")

    def _limpiar_formulario(self):
        self.label_foto.setText("Foto")
        self.label_foto.setStyleSheet("background-color: #333; border: 3px solid #555; border-radius: 75px; color: #AAA;")
        self.label_nombre.setText("Nombre del Socio")
        self.label_socio_id.setText("ID de Socio: N/A")
        self.label_plan.setText("Plan: N/A")
        self._actualizar_estado("Esperando...")
        
        # --- NUEVO: Limpiar video ---
        self.label_video.setText("El video de la cámara aparecerá aquí.")
        self.label_video.setStyleSheet("background-color: #000; border: 1px solid #555; border-radius: 5px; color: #AAA;")

        # Limpiar los nuevos labels de fecha
        self.label_fecha_inicio.setText("Inicio: --/--/----")
        self.label_fecha_fin.setText("Fin: --/--/----")
        self.label_dias_restantes.setText("Días restantes: N/A")

    def _crear_pixmap_circular(self, source_pixmap: QPixmap, size: int) -> QPixmap:
        """Recorta un QPixmap en forma circular."""
        if source_pixmap.isNull():
            return QPixmap()

        # Escalar la imagen para que encaje en el círculo, manteniendo la proporción
        # --- Lógica de escalado y recorte (Cover) ---
        # 1. Redimensionar la imagen para que el lado más corto mida 'size'
        #    Esto asegura que la imagen cubrirá completamente el círculo.
        if source_pixmap.width() < source_pixmap.height():
            scaled_pixmap = source_pixmap.scaledToWidth(size, Qt.TransformationMode.SmoothTransformation)
        else:
            scaled_pixmap = source_pixmap.scaledToHeight(size, Qt.TransformationMode.SmoothTransformation)

        # 2. Calcular el punto de inicio para dibujar la imagen centrada
        #    Esto efectivamente recorta la imagen desde el centro.
        x = (scaled_pixmap.width() - size) / 2
        y = (scaled_pixmap.height() - size) / 2

        target = QPixmap(size, size)
        target.fill(Qt.GlobalColor.transparent)

        path = QPainterPath()
        path.addEllipse(0, 0, size, size)

        painter = QPainter(target)
        painter.setClipPath(path)
        # Dibujar la porción central de la imagen escalada
        painter.drawPixmap(int(-x), int(-y), scaled_pixmap)
        painter.end()

        return target

    # --- MÉTODOS PARA IDENTIFICACIÓN POR HUELLA ---

    def _iniciar_identificacion_por_huella(self):
        if platform.system().lower() != "windows":
            self.label_estado_huella.setText("Identificación por huella no disponible en este SO.")
            return

        if self.identification_thread and self.identification_thread.isRunning():
            return

        self.identification_thread = IdentificationWorker()
        self.identification_thread.huella_capturada.connect(self._on_huella_identificada)
        self.identification_thread.error_sdk.connect(self._on_error_sdk_huella)
        self.identification_thread.estado_lector.connect(self._on_estado_lector_actualizado)
        self.identification_thread.start()

    def _detener_identificacion_por_huella(self):
        if self.identification_thread and self.identification_thread.isRunning():
            self.identification_thread.stop()
            self.identification_thread.wait() # Espera a que el hilo termine limpiamente
        self.identification_thread = None
        self.label_estado_huella.setText("Lector de huella detenido.")

    def _on_huella_identificada(self, fmd_capturado):
        try:
            self.label_estado_huella.setText("Huella capturada. Buscando en la base de datos...")
            socio_encontrado = self.servicios_socio.identificar_por_huella(fmd_capturado)

            if socio_encontrado:
                self._actualizar_credencial(socio_encontrado)
            else:
                self._limpiar_formulario()
                self._actualizar_estado("ACCESO DENEGADO", COLOR_ERROR)
                QMessageBox.warning(self, "No Encontrado", "La huella no coincide con ningún socio registrado.")

        except Exception as e:
            QMessageBox.critical(self, "Error de Identificación", f"Ocurrió un error al procesar la huella: {e}")
            self.label_estado_huella.setText("Error al procesar huella.")

    def _on_error_sdk_huella(self, mensaje):
        QMessageBox.critical(self, "Error de Lector de Huella", mensaje)
        self.label_estado_huella.setText(f"Error del SDK: {mensaje}")
        self._detener_identificacion_por_huella()

    def _on_estado_lector_actualizado(self, mensaje):
        self.label_estado_huella.setText(mensaje)

    # --- NUEVOS MÉTODOS PARA CÁMARA Y QR ---

    def _iniciar_busqueda_camaras(self):
        """Inicia el hilo para encontrar cámaras disponibles."""
        if self.discovery_thread and self.discovery_thread.isRunning():
            return
        
        self.combo_camaras.clear()
        self.combo_camaras.addItem("Buscando cámaras...")
        self.combo_camaras.setEnabled(False)
        self.btn_iniciar_camara.setEnabled(False)

        self.discovery_thread = CameraDiscoveryWorker()
        self.discovery_thread.camaras_encontradas.connect(self._on_camaras_encontradas)
        self.discovery_thread.start()

    def _detener_busqueda_camaras(self):
        if self.discovery_thread and self.discovery_thread.isRunning():
            self.discovery_thread.quit()
            self.discovery_thread.wait()

    def _on_camaras_encontradas(self, camaras: list):
        """Puebla el ComboBox cuando el hilo de búsqueda termina."""
        self.combo_camaras.clear()
        if camaras:
            self.combo_camaras.setEnabled(True)
            self.btn_iniciar_camara.setEnabled(True)
            for nombre_cam, indice_cam in camaras:
                self.combo_camaras.addItem(nombre_cam, userData=indice_cam)
        else:
            self.combo_camaras.addItem("No se encontraron cámaras")

    def _toggle_camara(self):
        """Inicia o detiene el hilo de la cámara."""
        if self.camera_thread and self.camera_thread.isRunning():
            self._detener_camara()
        else:
            self._iniciar_camara()

    def _iniciar_camara(self):
        if self.camera_thread and self.camera_thread.isRunning():
            return

        camera_index = self.combo_camaras.currentData()
        if camera_index is None:
            QMessageBox.warning(self, "Sin Cámara", "No hay una cámara seleccionada o disponible.")
            return

        self.camera_thread = CameraWorker(camera_index)
        self.camera_thread.frame_actualizado.connect(self._actualizar_frame_video)
        self.camera_thread.qr_detectado.connect(self._on_qr_detectado)
        self.camera_thread.estado_camara.connect(self.label_estado_huella.setText) # Reutilizamos el label de estado
        self.camera_thread.start()
        self.btn_iniciar_camara.setText("Detener Cámara")

    def _detener_camara(self):
        if self.camera_thread and self.camera_thread.isRunning():
            self.camera_thread.stop()
            # --- CORRECCIÓN CRÍTICA ---
            # No usamos wait() aquí. wait() bloquea el hilo principal de la UI, causando que la aplicación se congele.
            # Simplemente le decimos al hilo que se detenga y dejamos que termine en segundo plano.
        self.camera_thread = None
        self.btn_iniciar_camara.setText("Iniciar Cámara")
        self.label_video.setText("Cámara detenida.")

    def _actualizar_frame_video(self, q_image: QImage):
        """Muestra el fotograma de la cámara en el QLabel."""
        pixmap = QPixmap.fromImage(q_image)
        self.label_video.setPixmap(pixmap.scaled(self.label_video.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def _on_qr_detectado(self, qr_data: str):
        """Procesa los datos recibidos del código QR."""
        try:
            if qr_data.startswith("socio_id:"):
                socio_id = int(qr_data.split(":")[1])
                socio_encontrado = self.servicios_socio.obtener_socio_por_id(socio_id)

                if socio_encontrado:
                    self._actualizar_credencial(socio_encontrado)
                else:
                    self._limpiar_formulario()
                    self._actualizar_estado("ACCESO DENEGADO", COLOR_ERROR)
                    QMessageBox.warning(self, "No Encontrado", f"El socio con ID {socio_id} no fue encontrado.")
        except (ValueError, IndexError) as e:
            self.label_estado_huella.setText(f"QR no válido: {qr_data}")
