import ctypes
import os
import platform
import time
from PyQt6.QtCore import QThread, pyqtSignal

try:
    import win32event, win32api, win32gui, win32con, pythoncom
except ImportError:
    # Si pywin32 no está instalado, las funciones que lo usan fallarán,
    # pero el programa podrá iniciarse en sistemas no Windows.
    pass

# --- Tipos y Constantes del SDK de DigitalPersona ---
FT_HANDLE = ctypes.c_void_p
FT_RETCODE = ctypes.c_int
FT_BYTE = ctypes.c_ubyte
FT_BOOL = ctypes.c_int
FT_PRE_REG_FTR = 0
FT_REG_FTR = 1
FT_VER_FTR = 2 # Para verificación/identificación

HDPOPERATION = ctypes.c_ulong
HWND = ctypes.c_void_p
ULONG = ctypes.c_ulong
HRESULT = ctypes.c_long
GUID = (ctypes.c_ubyte * 16)

WM_USER = win32con.WM_USER if 'win32con' in globals() else 0x0400
WMUS_FP_NOTIFY = WM_USER + 101

WN_COMPLETED = 0
WN_ERROR = 1
WN_FINGER_TOUCHED = 5
WN_FINGER_GONE = 6

DP_PRIORITY_LOW = 3

class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ULONG), ("pbData", ctypes.POINTER(FT_BYTE))]

class MC_SETTINGS(ctypes.Structure):
    _fields_ = [("numPreRegFeatures", ctypes.c_int)]

class EnrollmentWorker(QThread):
    """
    Worker que maneja el proceso de enrolamiento de huella en un hilo separado.
    Utiliza DPFPApi.dll y un bucle de mensajes de Windows para una captura robusta.
    """
    proceso_finalizado = pyqtSignal(bytes, int)
    error_sdk = pyqtSignal(str)
    estado_actualizado = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._is_running = True
        self.dphftrex_dll = None
        self.dphmatch_dll = None
        self.dpfpapi_dll = None
        self.fx_context = FT_HANDLE(0)
        self.mc_context = FT_HANDLE(0)
        self.op_handle = HDPOPERATION(0)
        self.hwnd = 0
        self.class_atom = 0
        self.captures_needed = 4
        self.pre_enrollment_templates = []
        self.pre_reg_feature_len = 0

    def run(self):
        if platform.system().lower() != "windows":
            self.error_sdk.emit("La captura de huella solo es compatible con Windows.")
            return

        pythoncom.CoInitialize()
        try:
            self._load_and_init_sdk()
            self._create_invisible_window()
            self._start_acquisition()

            self.estado_actualizado.emit(f"Coloque el dedo {self.captures_needed} veces.")

            # Bucle de mensajes de Windows
            while self._is_running and len(self.pre_enrollment_templates) < self.captures_needed:
                msg = win32gui.PeekMessage(self.hwnd, 0, 0, win32con.PM_REMOVE)
                if msg[0] != 0:
                    if msg[1][1] == win32con.WM_QUIT:
                        self._is_running = False
                        break
                    win32gui.TranslateMessage(msg[1])
                    win32gui.DispatchMessage(msg[1])
                else:
                    self.msleep(50) # Pausa para no consumir 100% de CPU

            if self._is_running and len(self.pre_enrollment_templates) >= self.captures_needed:
                self._generate_final_template()

        except Exception as e:
            self.error_sdk.emit(f"Error en captura: {e}")
        finally:
            self._cleanup()
            pythoncom.CoUninitialize()

    def _load_and_init_sdk(self):
        try:
            self.dpfpapi_dll = ctypes.WinDLL('DPFPApi.dll')
            self.dphftrex_dll = ctypes.WinDLL('dpHFtrEx.dll')
            self.dphmatch_dll = ctypes.WinDLL('dpHMatch.dll')
        except OSError as e:
            raise Exception(f"Error al cargar DLLs: {e}. Asegúrese de que el RTE de DigitalPersona esté instalado.")

        # --- Definición de Prototipos (argtypes/restype) para dpfpapi_dll ---
        self.dpfpapi_dll.DPFPInit.restype = HRESULT
        self.dpfpapi_dll.DPFPTerm.restype = None
        self.dpfpapi_dll.DPFPCreateAcquisition.argtypes = [ctypes.c_int, ctypes.POINTER(GUID), ULONG, HWND, ULONG, ctypes.POINTER(HDPOPERATION)]
        self.dpfpapi_dll.DPFPCreateAcquisition.restype = HRESULT
        self.dpfpapi_dll.DPFPStartAcquisition.argtypes = [HDPOPERATION]
        self.dpfpapi_dll.DPFPStartAcquisition.restype = HRESULT
        self.dpfpapi_dll.DPFPStopAcquisition.argtypes = [HDPOPERATION]
        self.dpfpapi_dll.DPFPStopAcquisition.restype = HRESULT
        self.dpfpapi_dll.DPFPDestroyAcquisition.argtypes = [HDPOPERATION]
        self.dpfpapi_dll.DPFPDestroyAcquisition.restype = HRESULT
        self.dpfpapi_dll.DPFPBufferFree.argtypes = [ctypes.c_void_p]
        
        # --- Definición de Prototipos (argtypes/restype) para dphftrex_dll ---
        self.dphftrex_dll.FX_init.restype = FT_RETCODE
        self.dphftrex_dll.FX_createContext.argtypes = [ctypes.POINTER(FT_HANDLE)]
        self.dphftrex_dll.FX_createContext.restype = FT_RETCODE
        self.dphftrex_dll.FX_getFeaturesLen.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
        self.dphftrex_dll.FX_getFeaturesLen.restype = FT_RETCODE
        # Ajustado según tu ejemplo para usar ctypes.c_int para image_size, buffer_len y los punteros de calidad
        self.dphftrex_dll.FX_extractFeatures.argtypes = [FT_HANDLE, ctypes.c_int, ctypes.POINTER(FT_BYTE), ctypes.c_int, ctypes.c_int, ctypes.POINTER(FT_BYTE), ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int), ctypes.POINTER(FT_BOOL)]
        self.dphftrex_dll.FX_extractFeatures.restype = FT_RETCODE
        self.dphftrex_dll.FX_closeContext.argtypes = [FT_HANDLE]
        self.dphftrex_dll.FX_closeContext.restype = FT_RETCODE
        self.dphftrex_dll.FX_terminate.restype = FT_RETCODE

        # --- Definición de Prototipos (argtypes/restype) para dphmatch_dll ---
        self.dphmatch_dll.MC_init.restype = FT_RETCODE
        self.dphmatch_dll.MC_createContext.argtypes = [ctypes.POINTER(FT_HANDLE)]
        self.dphmatch_dll.MC_createContext.restype = FT_RETCODE
        self.dphmatch_dll.MC_getSettings.argtypes = [ctypes.POINTER(MC_SETTINGS)]
        self.dphmatch_dll.MC_getSettings.restype = FT_RETCODE
        self.dphmatch_dll.MC_getFeaturesLen.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
        self.dphmatch_dll.MC_getFeaturesLen.restype = FT_RETCODE
        self.dphmatch_dll.MC_generateRegFeatures.argtypes = [FT_HANDLE, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.POINTER(FT_BYTE)), ctypes.c_int, ctypes.POINTER(FT_BYTE), ctypes.c_void_p, ctypes.POINTER(FT_BOOL)]
        self.dphmatch_dll.MC_generateRegFeatures.restype = FT_RETCODE
        # self.dphmatch_dll.MC_verifyFeaturesEx.argtypes = [FT_HANDLE, ctypes.c_int, ctypes.POINTER(FT_BYTE), ctypes.c_int, ctypes.POINTER(FT_BYTE), ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_double), ctypes.POINTER(FT_BOOL)]
        # self.dphmatch_dll.MC_verifyFeaturesEx.restype = FT_RETCODE
        self.dphmatch_dll.MC_closeContext.argtypes = [FT_HANDLE]
        self.dphmatch_dll.MC_closeContext.restype = FT_RETCODE
        self.dphmatch_dll.MC_terminate.restype = FT_RETCODE

        # --- Inicialización de los SDKs ---
        if self.dpfpapi_dll.DPFPInit() != 0: raise Exception("Fallo al inicializar DPFPInit")
        if self.dphftrex_dll.FX_init() != 0: raise Exception("Fallo al inicializar FX_init")
        if self.dphmatch_dll.MC_init() != 0: raise Exception("Fallo al inicializar MC_init")

        if self.dphftrex_dll.FX_createContext(ctypes.byref(self.fx_context)) != 0: raise Exception("Fallo al crear contexto FX")
        if self.dphmatch_dll.MC_createContext(ctypes.byref(self.mc_context)) != 0: raise Exception("Fallo al crear contexto MC")

        mc_settings = MC_SETTINGS()
        self.dphmatch_dll.MC_getSettings(ctypes.byref(mc_settings))
        self.captures_needed = mc_settings.numPreRegFeatures

        pre_reg_feature_len_ptr = ctypes.c_int(0)
        self.dphftrex_dll.FX_getFeaturesLen(FT_PRE_REG_FTR, ctypes.byref(pre_reg_feature_len_ptr), None)
        self.pre_reg_feature_len = pre_reg_feature_len_ptr.value

    def _create_invisible_window(self):
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self._wnd_proc
        wc.lpszClassName = "FingerprintListener"
        wc.hInstance = win32api.GetModuleHandle(None)
        self.class_atom = win32gui.RegisterClass(wc)
        self.hwnd = win32gui.CreateWindow(self.class_atom, "FP Listener", 0, 0, 0, 0, 0, 0, 0, wc.hInstance, None)
        if not self.hwnd:
            raise Exception("No se pudo crear la ventana invisible para el lector.")

    def _start_acquisition(self):
        GUID_NULL = GUID()
        hr = self.dpfpapi_dll.DPFPCreateAcquisition(DP_PRIORITY_LOW, ctypes.byref(GUID_NULL), 4, self.hwnd, WMUS_FP_NOTIFY, ctypes.byref(self.op_handle))
        if hr != 0: raise Exception(f"Fallo en DPFPCreateAcquisition: {hr}")

        hr = self.dpfpapi_dll.DPFPStartAcquisition(self.op_handle)
        if hr != 0: raise Exception(f"Fallo en DPFPStartAcquisition: {hr}")

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WMUS_FP_NOTIFY:
            event_type = wparam
            if event_type == WN_FINGER_TOUCHED:
                self.estado_actualizado.emit("Dedo detectado. Mantenga quieto.")
            elif event_type == WN_FINGER_GONE:
                capturas_restantes = self.captures_needed - len(self.pre_enrollment_templates)
                if capturas_restantes > 0:
                    self.estado_actualizado.emit(f"¡Bien! Levante el dedo. Faltan {capturas_restantes} capturas.")
            elif event_type == WN_COMPLETED:
                image_blob_ptr = ctypes.cast(lparam, ctypes.POINTER(DATA_BLOB))
                self._process_fingerprint_sample(image_blob_ptr)
            elif event_type == WN_ERROR:
                self.error_sdk.emit(f"Error del lector: {lparam}")
                self.stop()
            return 0
        elif msg == win32con.WM_DESTROY or msg == win32con.WM_CLOSE:
            win32gui.PostQuitMessage(0)
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _process_fingerprint_sample(self, image_blob_ptr):
        try:
            if not image_blob_ptr or not image_blob_ptr.contents.pbData or image_blob_ptr.contents.cbData == 0:
                self.estado_actualizado.emit("Error: Datos de imagen inválidos.")
                return

            image_size = image_blob_ptr.contents.cbData
            image_data_ptr = image_blob_ptr.contents.pbData
            image_data_copy = ctypes.string_at(image_data_ptr, image_size)

            buffer = (FT_BYTE * self.pre_reg_feature_len)()
            features_created = FT_BOOL(0)
            image_data_ctype = (FT_BYTE * image_size).from_buffer_copy(image_data_copy)
            
            # --- CORRECCIÓN CRUCIAL ---
            # Creamos variables para recibir los valores de calidad, aunque no los usemos.
            # La función espera punteros válidos, no punteros nulos (None).
            image_quality = ctypes.c_int(0)
            feature_quality = ctypes.c_int(0)

            rc = self.dphftrex_dll.FX_extractFeatures(
                self.fx_context, ctypes.c_int(image_size), ctypes.cast(image_data_ctype, ctypes.POINTER(FT_BYTE)), FT_PRE_REG_FTR, self.pre_reg_feature_len, buffer, ctypes.byref(image_quality), ctypes.byref(feature_quality), ctypes.byref(features_created)
            )

            if rc == 0 and features_created.value:
                feature_set_bytes = bytes(buffer)
                self.pre_enrollment_templates.append(feature_set_bytes)
                capturas_hechas = len(self.pre_enrollment_templates)
                self.estado_actualizado.emit(f"Captura {capturas_hechas}/{self.captures_needed} exitosa.")
            else:
                self.estado_actualizado.emit("Fallo en captura. Intente de nuevo.")
        except Exception as e:
            self.error_sdk.emit(f"Error procesando huella: {e}")
        # No se debe llamar a DPFPBufferFree aquí. El SDK gestiona la liberación
        # del búfer de imagen (lparam) después de que el manejador de mensajes retorna.

    def _generate_final_template(self):
        try:
            self.estado_actualizado.emit("Generando plantilla final...")

            reg_template_len_ptr = ctypes.c_int(0)
            self.dphmatch_dll.MC_getFeaturesLen(FT_REG_FTR, 0, ctypes.byref(reg_template_len_ptr), None)
            reg_template_len = reg_template_len_ptr.value
            reg_template_buffer = (FT_BYTE * reg_template_len)()

            template_created = FT_BOOL(0)
            PunteroArrayFT_BYTE = ctypes.POINTER(FT_BYTE) * self.captures_needed
            feature_set_pointers = PunteroArrayFT_BYTE()
            
            # Es crucial mantener vivos los buffers temporales durante la llamada a C
            buffers_temporales = []
            for i, fs_bytes in enumerate(self.pre_enrollment_templates):
                temp_buffer = (FT_BYTE * self.pre_reg_feature_len).from_buffer_copy(fs_bytes)
                buffers_temporales.append(temp_buffer)
                feature_set_pointers[i] = ctypes.cast(temp_buffer, ctypes.POINTER(FT_BYTE))

            rc = self.dphmatch_dll.MC_generateRegFeatures(
                self.mc_context, 0, self.captures_needed, self.pre_reg_feature_len,
                feature_set_pointers, reg_template_len, reg_template_buffer, None,
                ctypes.byref(template_created)
            )

            if rc == 0 and template_created.value:
                final_template = bytes(reg_template_buffer)
                self.proceso_finalizado.emit(final_template, len(final_template))
            else:
                self.error_sdk.emit(f"No se pudo generar la plantilla final. Código: {rc}")
        except Exception as e:
            self.error_sdk.emit(f"Error generando plantilla: {e}")
        finally:
            self.stop()

    def stop(self):
        self._is_running = False
        if self.hwnd:
            win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)

    def _cleanup(self):
        if self.op_handle and self.op_handle.value:
            self.dpfpapi_dll.DPFPStopAcquisition(self.op_handle)
            self.dpfpapi_dll.DPFPDestroyAcquisition(self.op_handle)
            self.op_handle = HDPOPERATION(0)

        if self.mc_context and self.mc_context.value:
            self.dphmatch_dll.MC_closeContext(self.mc_context)
            self.mc_context = FT_HANDLE(0)

        if self.fx_context and self.fx_context.value:
            self.dphftrex_dll.FX_closeContext(self.fx_context)
            self.fx_context = FT_HANDLE(0)

        if self.dphmatch_dll: self.dphmatch_dll.MC_terminate()
        if self.dphftrex_dll: self.dphftrex_dll.FX_terminate()
        if self.dpfpapi_dll: self.dpfpapi_dll.DPFPTerm()

        if self.hwnd:
            win32gui.DestroyWindow(self.hwnd)
            self.hwnd = 0
        if self.class_atom:
            win32gui.UnregisterClass(self.class_atom, win32api.GetModuleHandle(None))
            self.class_atom = 0

class IdentificationWorker(QThread):
    """
    Worker que maneja la captura de una huella para identificación en un hilo separado.
    Emite la plantilla capturada para que sea comparada con la base de datos.
    """
    huella_capturada = pyqtSignal(bytes)
    error_sdk = pyqtSignal(str)
    estado_lector = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._is_running = True
        self.dpfpapi_dll = None
        self.dphftrex_dll = None
        self.fx_context = FT_HANDLE(0)
        self.op_handle = HDPOPERATION(0)
        self.hwnd = 0
        self.class_atom = 0
        self.ver_feature_len = 0

    def run(self):
        if platform.system().lower() != "windows":
            self.error_sdk.emit("La identificación por huella solo es compatible con Windows.")
            return

        pythoncom.CoInitialize()
        try:
            self._load_and_init_sdk()
            self._create_invisible_window()
            self._start_acquisition()

            self.estado_lector.emit("Lector de huellas activo. Coloque el dedo para identificar.")

            # Bucle de mensajes de Windows
            while self._is_running:
                msg = win32gui.PeekMessage(self.hwnd, 0, 0, win32con.PM_REMOVE)
                if msg[0] != 0:
                    if msg[1][1] == win32con.WM_QUIT:
                        self._is_running = False
                        break
                    win32gui.TranslateMessage(msg[1])
                    win32gui.DispatchMessage(msg[1])
                else:
                    self.msleep(50) # Pausa para no consumir 100% de CPU

        except Exception as e:
            self.error_sdk.emit(f"Error en identificación: {e}")
        finally:
            self._cleanup()
            pythoncom.CoUninitialize()

    def _load_and_init_sdk(self):
        try:
            self.dpfpapi_dll = ctypes.WinDLL('DPFPApi.dll')
            self.dphftrex_dll = ctypes.WinDLL('dpHFtrEx.dll')
        except OSError as e:
            raise Exception(f"Error al cargar DLLs: {e}. Asegúrese de que el RTE de DigitalPersona esté instalado.")

        # --- Definición de Prototipos (argtypes/restype) para dpfpapi_dll ---
        self.dpfpapi_dll.DPFPInit.restype = HRESULT
        self.dpfpapi_dll.DPFPTerm.restype = None
        self.dpfpapi_dll.DPFPCreateAcquisition.argtypes = [ctypes.c_int, ctypes.POINTER(GUID), ULONG, HWND, ULONG, ctypes.POINTER(HDPOPERATION)]
        self.dpfpapi_dll.DPFPCreateAcquisition.restype = HRESULT
        self.dpfpapi_dll.DPFPStartAcquisition.argtypes = [HDPOPERATION]
        self.dpfpapi_dll.DPFPStartAcquisition.restype = HRESULT
        self.dpfpapi_dll.DPFPStopAcquisition.argtypes = [HDPOPERATION]
        self.dpfpapi_dll.DPFPStopAcquisition.restype = HRESULT
        self.dpfpapi_dll.DPFPDestroyAcquisition.argtypes = [HDPOPERATION]
        self.dpfpapi_dll.DPFPDestroyAcquisition.restype = HRESULT
        
        # --- Definición de Prototipos (argtypes/restype) para dphftrex_dll ---
        self.dphftrex_dll.FX_init.restype = FT_RETCODE
        self.dphftrex_dll.FX_createContext.argtypes = [ctypes.POINTER(FT_HANDLE)]
        self.dphftrex_dll.FX_createContext.restype = FT_RETCODE
        self.dphftrex_dll.FX_getFeaturesLen.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
        self.dphftrex_dll.FX_getFeaturesLen.restype = FT_RETCODE
        self.dphftrex_dll.FX_extractFeatures.argtypes = [FT_HANDLE, ctypes.c_int, ctypes.POINTER(FT_BYTE), ctypes.c_int, ctypes.c_int, ctypes.POINTER(FT_BYTE), ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int), ctypes.POINTER(FT_BOOL)]
        self.dphftrex_dll.FX_extractFeatures.restype = FT_RETCODE
        self.dphftrex_dll.FX_closeContext.argtypes = [FT_HANDLE]
        self.dphftrex_dll.FX_closeContext.restype = FT_RETCODE
        self.dphftrex_dll.FX_terminate.restype = FT_RETCODE

        # --- Inicialización de los SDKs ---
        if self.dpfpapi_dll.DPFPInit() != 0: raise Exception("Fallo al inicializar DPFPInit")
        if self.dphftrex_dll.FX_init() != 0: raise Exception("Fallo al inicializar FX_init")

        if self.dphftrex_dll.FX_createContext(ctypes.byref(self.fx_context)) != 0: raise Exception("Fallo al crear contexto FX")

        ver_feature_len_ptr = ctypes.c_int(0)
        self.dphftrex_dll.FX_getFeaturesLen(FT_VER_FTR, ctypes.byref(ver_feature_len_ptr), None)
        self.ver_feature_len = ver_feature_len_ptr.value

    def _create_invisible_window(self):
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self._wnd_proc
        wc.lpszClassName = "FingerprintIdentifier"
        wc.hInstance = win32api.GetModuleHandle(None)
        self.class_atom = win32gui.RegisterClass(wc)
        self.hwnd = win32gui.CreateWindow(self.class_atom, "FP Identifier", 0, 0, 0, 0, 0, 0, 0, wc.hInstance, None)
        if not self.hwnd:
            raise Exception("No se pudo crear la ventana invisible para el lector.")

    def _start_acquisition(self):
        GUID_NULL = GUID()
        hr = self.dpfpapi_dll.DPFPCreateAcquisition(DP_PRIORITY_LOW, ctypes.byref(GUID_NULL), 4, self.hwnd, WMUS_FP_NOTIFY, ctypes.byref(self.op_handle))
        if hr != 0: raise Exception(f"Fallo en DPFPCreateAcquisition: {hr}")

        hr = self.dpfpapi_dll.DPFPStartAcquisition(self.op_handle)
        if hr != 0: raise Exception(f"Fallo en DPFPStartAcquisition: {hr}")

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WMUS_FP_NOTIFY:
            event_type = wparam
            if event_type == WN_FINGER_TOUCHED:
                self.estado_lector.emit("Dedo detectado. Procesando...")
            elif event_type == WN_FINGER_GONE:
                self.estado_lector.emit("Lector de huellas activo. Coloque el dedo para identificar.")
            elif event_type == WN_COMPLETED:
                image_blob_ptr = ctypes.cast(lparam, ctypes.POINTER(DATA_BLOB))
                self._process_fingerprint_sample(image_blob_ptr)
            elif event_type == WN_ERROR:
                self.error_sdk.emit(f"Error del lector: {lparam}")
            return 0
        elif msg == win32con.WM_DESTROY or msg == win32con.WM_CLOSE:
            win32gui.PostQuitMessage(0)
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _process_fingerprint_sample(self, image_blob_ptr):
        try:
            if not image_blob_ptr or not image_blob_ptr.contents.pbData or image_blob_ptr.contents.cbData == 0:
                self.estado_lector.emit("Error: Datos de imagen inválidos.")
                return

            image_size = image_blob_ptr.contents.cbData
            image_data_ptr = image_blob_ptr.contents.pbData
            image_data_copy = ctypes.string_at(image_data_ptr, image_size)

            buffer = (FT_BYTE * self.ver_feature_len)()
            features_created = FT_BOOL(0)
            image_data_ctype = (FT_BYTE * image_size).from_buffer_copy(image_data_copy)
            
            image_quality = ctypes.c_int(0)
            feature_quality = ctypes.c_int(0)

            rc = self.dphftrex_dll.FX_extractFeatures(
                self.fx_context, ctypes.c_int(image_size), ctypes.cast(image_data_ctype, ctypes.POINTER(FT_BYTE)), FT_VER_FTR, self.ver_feature_len, buffer, ctypes.byref(image_quality), ctypes.byref(feature_quality), ctypes.byref(features_created)
            )

            if rc == 0 and features_created.value:
                feature_set_bytes = bytes(buffer)
                self.huella_capturada.emit(feature_set_bytes)
            else:
                self.estado_lector.emit("Fallo en captura. Intente de nuevo.")
        except Exception as e:
            self.error_sdk.emit(f"Error procesando huella: {e}")

    def stop(self):
        self._is_running = False
        if self.hwnd:
            win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)

    def _cleanup(self):
        if self.op_handle and self.op_handle.value:
            self.dpfpapi_dll.DPFPStopAcquisition(self.op_handle)
            self.dpfpapi_dll.DPFPDestroyAcquisition(self.op_handle)
            self.op_handle = HDPOPERATION(0)

        if self.fx_context and self.fx_context.value:
            self.dphftrex_dll.FX_closeContext(self.fx_context)
            self.fx_context = FT_HANDLE(0)

        if self.dphftrex_dll: self.dphftrex_dll.FX_terminate()
        if self.dpfpapi_dll: self.dpfpapi_dll.DPFPTerm()

        if self.hwnd:
            win32gui.DestroyWindow(self.hwnd)
            self.hwnd = 0
        if self.class_atom:
            win32gui.UnregisterClass(self.class_atom, win32api.GetModuleHandle(None))
            self.class_atom = 0