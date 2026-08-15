# core/webhooks.py
import json
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from core.models import BotSession
from inventario.models import ItemInventario
import os

# Este token te lo da "BotFather" gratis al crear tu bot en Telegram
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_API_URL = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'


def enviar_mensaje_telegram(chat_id, texto):
    """Función auxiliar para disparar el mensaje de vuelta a Telegram"""
    payload = {
        'chat_id': chat_id,
        'text': texto,
        'parse_mode': 'Markdown'
    }
    requests.post(TELEGRAM_API_URL, json=payload)


# csrf_exempt es VITAL porque Telegram no tiene nuestro token de seguridad de Django
@csrf_exempt
def webhook_telegram(request):
    if request.method == 'POST':
        try:
            # 1. Leemos el mensaje que nos mandó Telegram
            data = json.loads(request.body)

            if 'message' not in data:
                return JsonResponse({'status': 'ok'})

            chat_id = data['message']['chat']['id']
            texto = data['message'].get('text', '').strip()

            # 2. Seguridad: ¿Conocemos a la persona que escribe?
            sesion = BotSession.objects.filter(chat_id=chat_id, plataforma='TELEGRAM', activo=True).first()

            if not sesion:
                # Si es un desconocido, le decimos su ID para que el administrador lo registre
                enviar_mensaje_telegram(chat_id,
                                        f"🔒 Acceso denegado. Tu Chat ID es `{chat_id}`. Pide a tu gerente que lo vincule a tu cuenta.")
                return JsonResponse({'status': 'ok'})

            # 3. Lógica de Negocio: Buscar en el inventario de SU sucursal
            sucursal = sesion.usuario.sucursal
            resultados = ItemInventario.objects.filter(
                Q(nombre__icontains=texto) | Q(codigo_barras__icontains=texto),
                sucursal=sucursal
            )[:3]  # Limitamos a 3 para no llenar la pantalla del celular

            # 4. Armamos la respuesta y se la enviamos
            if resultados:
                respuesta = f"📦 *Búsqueda:* '{texto}'\n\n"
                for item in resultados:
                    respuesta += f"🔹 *{item.nombre}*\n"
                    respuesta += f"Stock disponible: {item.stock}\n"
                    respuesta += f"Ubicación: Pasillo {item.ubicacion_pasillo or 'N/A'}, Cajón {item.ubicacion_cajon or 'N/A'}\n\n"
            else:
                respuesta = f"❌ No encontré '{texto}' en el inventario de la sucursal {sucursal.nombre}."

            enviar_mensaje_telegram(chat_id, respuesta)

        except Exception as e:
            # Evitamos que el webhook colapse si Telegram manda algo raro
            print(f"Error en webhook: {e}")

        # Siempre debemos responderle un "OK" (200) a Telegram rápido, sino intentará reenviar el mensaje
        return JsonResponse({'status': 'ok'})

    return JsonResponse({'error': 'Método no permitido'}, status=405)