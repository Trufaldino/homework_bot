import logging
import os
import time
import requests
from telegram import Bot
from dotenv import load_dotenv
from http import HTTPStatus
from exceptions import SendMessageError, EndpointError


load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='homework.log',
    level=logging.INFO)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(f'Сообщение: {message} - успешно отправлено')
    except SendMessageError as error:
        logging.error(f'сбой при отправке сообщения в Telegram: {error}.')
    return message


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp  # or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except EndpointError as error:
        logging.error(f'Эндпоинт {ENDPOINT} недоступен: {error}.')
        logging.error(f'отсутствие ожидаемых ключей в ответе API: {response}')
    if response.status_code == HTTPStatus.OK:
        response = response.json()
        return response  # <class 'dict'>
    else:
        raise EndpointError('Неверный статус код.')


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict) or response is None:
        message = 'Ответ API не содержит словаря с данными'
        raise TypeError(message)
    elif any([response.get('homeworks') is None,
              response.get('current_date') is None]):
        message = ('Словарь ответа API не содержит ключей homeworks и/или '
                   'current_date')
        raise KeyError(message)
    elif not isinstance(response.get('homeworks'), list):
        message = 'Ключ homeworks в ответе API не содержит списка'
        raise TypeError(message)
    elif not response.get('homeworks'):
        logging.debug('Статус проверки не изменился')
        return []
    else:
        homework = response.get('homeworks')
        return homework  # <class 'list'>


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе ее статус."""
    homework_status = homework.get('status')
    homework_name = homework.get('homework_name')
    if homework_status in HOMEWORK_STATUSES:
        verdict = HOMEWORK_STATUSES.get(homework_status)
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    elif homework_status not in HOMEWORK_STATUSES:
        verdict = 'Твоя работа еще не проверена :('
        logging.debug(f'отсутствие в ответе новых статусов: {verdict}')
        raise KeyError(verdict)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all(
        [
            PRACTICUM_TOKEN is not None,
            TELEGRAM_TOKEN is not None,
            TELEGRAM_CHAT_ID is not None,
        ]
    )


def main():
    """Основная логика работы бота."""
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 0
    api_answer = get_api_answer(current_timestamp)
    response = check_response(response=api_answer)
    status = parse_status(homework=response[0])
    while check_tokens():
        try:
            send_message(bot, message=status)
            time.sleep(RETRY_TIME)
        except Exception as error:
            error_message = f'Сбой в работе программы: {error}'
            send_message(bot, message=error_message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
