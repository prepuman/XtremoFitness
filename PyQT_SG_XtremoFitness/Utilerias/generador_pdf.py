import os
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors, utils
from reportlab.platypus import Image
import io

from dominio.modelos import SocioModel, MembresiaModel

# Definimos un tamaño de página personalizado para el voucher (ancho x alto en puntos)
# 4 x 6 pulgadas, un tamaño común para vouchers o fotos.
VOUCHER_SIZE = (4 * inch, 6 * inch)

def generar_voucher_socio(socio: SocioModel, membresia: MembresiaModel, ruta_salida: str):
    """
    Genera un voucher en PDF para un socio y su membresía.
    """
    try:
        c = canvas.Canvas(ruta_salida, pagesize=VOUCHER_SIZE)
        ancho, alto = VOUCHER_SIZE

        # --- Título ---
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(ancho / 2, alto - 0.75 * inch, "Xtremo Fitness")
        c.setFont("Helvetica", 12)
        c.drawCentredString(ancho / 2, alto - 1 * inch, "Comprobante de Inscripción")

        # --- Línea divisoria ---
        c.setStrokeColor(colors.black)
        c.line(0.5 * inch, alto - 1.2 * inch, ancho - 0.5 * inch, alto - 1.2 * inch)

        # --- Datos del Socio ---
        y_pos = alto - 1.5 * inch
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.5 * inch, y_pos, "Datos del Socio:")

        c.setFont("Helvetica", 9)
        nombre_completo = f"{socio.nombre} {socio.apellido_paterno} {socio.apellido_materno or ''}".strip()
        c.drawString(0.7 * inch, y_pos - 0.25 * inch, f"Nombre: {nombre_completo}")
        c.drawString(0.7 * inch, y_pos - 0.45 * inch, f"ID de Socio: {socio.id:05d}")

        # --- Datos de la Membresía ---
        y_pos -= 1 * inch
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.5 * inch, y_pos, "Detalles de la Membresía:")

        c.setFont("Helvetica", 9)
        c.drawString(0.7 * inch, y_pos - 0.25 * inch, f"Plan Contratado: {membresia.plan.nombre}")
        c.drawString(0.7 * inch, y_pos - 0.45 * inch, f"Precio: ${membresia.plan.precio:,.2f} MXN")
        c.drawString(0.7 * inch, y_pos - 0.65 * inch, f"Fecha de Inicio: {membresia.fecha_inicio.strftime('%d / %b / %Y')}")
        c.drawString(0.7 * inch, y_pos - 0.85 * inch, f"Fecha de Vencimiento: {membresia.fecha_fin.strftime('%d / %b / %Y')}")

        # --- Código QR ---
        if socio.qr_code:
            try:
                # ReportLab puede dibujar una imagen desde un objeto de archivo en memoria
                qr_image = utils.ImageReader(io.BytesIO(socio.qr_code))
                # --- NUEVO: Centrar el QR horizontalmente ---
                qr_ancho = 1.25 * inch
                c.drawImage(qr_image, (ancho - qr_ancho) / 2, 1.2 * inch, width=qr_ancho, height=1.25*inch, preserveAspectRatio=True)
            except Exception as e:
                print(f"No se pudo dibujar el QR en el PDF: {e}")


        # --- Sección de Firma ---
        y_pos_firma = 0.85 * inch # Se baja la línea de la firma
        c.line(ancho / 2 - 1.25 * inch, y_pos_firma, ancho / 2 + 1.25 * inch, y_pos_firma)
        c.setFont("Helvetica", 8)
        c.drawCentredString(ancho / 2, y_pos_firma - 0.15 * inch, "Firma del Socio") # El texto se ajusta automáticamente

        # --- Pie de página ---
        c.setFont("Helvetica-Oblique", 7)
        fecha_emision = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        c.drawString(0.5 * inch, 0.5 * inch, f"Emitido el: {fecha_emision}")
        c.drawRightString(ancho - 0.5 * inch, 0.5 * inch, "Gracias por su preferencia")

        # --- Logo (Opcional) ---
        logo_path = "./Imagenes/logo.png"
        if os.path.exists(logo_path):
            # Usamos platypus.Image para manejar el tamaño y la proporción
            logo = Image(logo_path, width=0.75*inch, height=0.75*inch)
            logo.hAlign = 'LEFT'
            # Dibujamos el logo en la esquina superior izquierda
            logo.drawOn(c, 0.5 * inch, alto - 1 * inch)

        c.save()
        return True, None

    except Exception as e:
        return False, str(e)

def abrir_archivo(ruta_archivo: str):
    """
    Abre un archivo con la aplicación predeterminada del sistema operativo.
    Simplificado para funcionar solo en Windows.
    """
    try:
        os.startfile(ruta_archivo)
        return True, None
    except FileNotFoundError as e:
        return False, f"No se pudo abrir el archivo. Es posible que no tenga un visor de PDF instalado. Error: {e}"
    except Exception as e:
        return False, f"Ocurrió un error inesperado al intentar abrir el archivo: {e}"