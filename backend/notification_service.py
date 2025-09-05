import requests
import logging

def send_telegram_alert(bot_token, chat_id, message):
    """
    Envia uma mensagem de alerta para um chat do Telegram.
    Esta função é auto-contida e não depende de GUI.
    """
    if not bot_token or "AQUI" in str(bot_token) or not chat_id or "AQUI" in str(chat_id):
        logging.warning("Token ou Chat ID do Telegram não configurado. Pulando notificação.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logging.info("Alerta enviado para o Telegram com sucesso.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao enviar alerta para o Telegram: {e}")
    except Exception as e:
        logging.error(f"Erro inesperado ao enviar para o Telegram: {e}")