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