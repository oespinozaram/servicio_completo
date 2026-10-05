# taller/utils.py
import requests
import os
import logging

logger = logging.getLogger(__name__)

# Estos datos te los dará Meta (Facebook) al crear tu App de WhatsApp Business
# Por ahora los pondremos aquí, pero en producción irán en tu settings.py o variables de entorno
WHATSAPP_API_TOKEN = os.environ.get('WHATSAPP_API_TOKEN')
WHATSAPP_PHONE_ID = os.environ.get('WHATSAPP_PHONE_ID')


def enviar_notificacion_whatsapp(telefono, nombre_cliente, marca_bici, total):
    """
    Envía un mensaje automático de WhatsApp usando la API oficial de Meta.
    """
    # Meta requiere el teléfono con código de país sin el '+' (ej. 52 para México)
    # Aquí podrías agregar lógica para limpiar el número
    telefono_limpio = ''.join(filter(str.isdigit, str(telefono)))

    url = f"https://graph.facebook.com/v17.0/{WHATSAPP_PHONE_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_API_TOKEN}",
        "Content-Type": "application/json"
    }

    mensaje = (
        f"Hola {nombre_cliente} 👋\n\n"
        f"¡Excelentes noticias! Tu bicicleta *{marca_bici}* ya está lista y reparada en nuestro taller. 🚲✨\n\n"
        f"El total a pagar es de: *${total}*.\n\n"
        f"Te esperamos para entregártela. ¡Gracias por tu preferencia!"
    )

    payload = {
        "messaging_product": "whatsapp",
        "to": telefono_limpio,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": mensaje
        }
    }

    try:
        # Hacemos la petición a los servidores de WhatsApp (timeout corto para no trabar el sistema)
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        response.raise_for_status()  # Lanza error si Meta responde con algo distinto a 200 OK
        return True
    except requests.exceptions.RequestException as e:
        # Si falla (ej. teléfono incorrecto o no hay internet), registramos el error pero NO tumbamos el sistema
        logger.error(f"Error al enviar WhatsApp a {telefono_limpio}: {e}")
        return False


# URL pública donde el cliente puede consultar los documentos legales.
# Centralizada aquí para cambiarla en un solo lugar cuando el dominio cambie.
LEGAL_URL = "https://www.serviciocompleto.app/legal"


def enviar_bienvenida_whatsapp(telefono, nombre_cliente, marca_bici, es_primera_vez=False):
    """
    Envía la confirmación de recepción cuando se crea una nueva OrdenTrabajo.

    Si es_primera_vez=True (primera orden histórica del cliente), adjunta el bloque
    legal con Términos y Condiciones + Aviso de Privacidad.
    Si es_primera_vez=False, omite ese bloque para no ser repetitivo.

    Args:
        telefono (str): Número del cliente (se limpia de caracteres no numéricos).
        nombre_cliente (str): Nombre para personalizar el saludo.
        marca_bici (str): Marca/modelo de la bicicleta recibida.
        es_primera_vez (bool): True si esta es la primera orden histórica del cliente.

    Returns:
        bool: True si Meta respondió 200 OK, False en cualquier error.
    """
    telefono_limpio = ''.join(filter(str.isdigit, str(telefono)))

    # ── Mensaje base de confirmación de recepción ─────────────────────────
    mensaje = (
        f"Hola {nombre_cliente} \U0001f44b\n\n"
        f"Hemos recibido tu bicicleta *{marca_bici}* en nuestro taller. \u2705\n"
        f"Pronto te contactaremos con el diagn\u00f3stico y presupuesto.\n\n"
        f"\u00a1Gracias por confiar en nosotros! \U0001f6b2"
    )

    # ── Bloque legal: solo se agrega en la PRIMERA orden del cliente ───────
    if es_primera_vez:
        mensaje += (
            f"\n\n---\n"
            f"\U0001f4cb *Aviso Legal:* Al utilizar nuestro servicio aceptas nuestros "
            f"T\u00e9rminos y Condiciones y Aviso de Privacidad.\n"
            f"Cons\u00faltalos en: {LEGAL_URL}"
        )

    url = f"https://graph.facebook.com/v17.0/{WHATSAPP_PHONE_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_API_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": telefono_limpio,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": mensaje,
        },
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al enviar WhatsApp de bienvenida a {telefono_limpio}: {e}")
        return False
