import qrcode
import io

def generar_qr_como_bytes(data: str, box_size: int = 10, border: int = 4) -> bytes:
    """
    Genera un código QR a partir de los datos proporcionados y lo devuelve como bytes en formato PNG.

    Args:
        data (str): La información a codificar en el QR.
        box_size (int): El tamaño de cada "caja" del QR.
        border (int): El grosor del borde del QR.

    Returns:
        bytes: Los datos de la imagen del QR en formato PNG.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    # Guardar la imagen en un buffer en memoria como PNG
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()

