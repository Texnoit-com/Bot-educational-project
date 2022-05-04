"""Модуль обработки состояние домашних заданий."""

import http
import logging
import os
import time
from json.decoder import JSONDecodeError

import requests
from dotenv import load_dotenv
from telegram import Bot, TelegramError

load_dotenv()
PRACTICUM_TOKEN: str = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID: int = os.getenv('TELEGRAM_CHAT_ID')
RETRY_TIME: int = 10000
MONTH_AGO: int = 2690000
ENDPOINT: str = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS: str = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORK_STATUSES: dict = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s')
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


def send_message(bot: Bot, message: str) -> None:
    """Формирование сообщения для бота."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Сообщение успешно отправленно: {message}')
    except TelegramError as error:
        logger.error(f'Сообщение не отправленно: {error}')


def get_api_answer(current_timestamp: int) -> dict:
    """Получения данных по API."""
    timestamp: int = current_timestamp or int(time.time())
    params: dict = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params=params)
        if response.status_code != http.HTTPStatus.OK:
            logger.error('Страница недоступна')
            raise http.exceptions.HTTPError()
        return response.json()
    except requests.exceptions.ConnectionError:
        logger.error('Ошибка подключения')
    except requests.exceptions.RequestException as request_error:
        logger.error(f'Ошибка запроса {request_error}')
    except JSONDecodeError:
        logger.error('JSON не сформирован')


def check_response(response: dict) -> dict:
    """Проверка ответа API на корректность."""
    if type(response) is not dict:
        raise TypeError('В функцию "check_response" поступил не словарь')
    if 'homeworks' not in response:
        raise KeyError('Ключ homeworks отсутствует')
    if type(response['homeworks']) is not list:
        raise TypeError('Объект homeworks не является списком')
    if response['homeworks'] == []:
        return {}
    return response.get('homeworks')[0]


def parse_status(homework: dict) -> str:
    """Парсинг ответа на запрос."""
    if 'status' not in homework or type(homework) is str:
        logger.error('Ключ status отсутствует в homework')
        raise KeyError('Ключ status отсутствует в homework')
    if 'homework_name' not in homework:
        raise KeyError('Ключ homework_name отсутствует в homework')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES.keys():
        raise ValueError('Значение не соответствует справочнику статусов')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Проверка наличия токенов."""
    for element in (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID):
        if element is None:
            logger.critical(f'Токен не задан: {element=}',)
            return False
    return True


def main() -> None:
    """Основная логика работы бота."""
    if not check_tokens():
        raise ValueError('Отсутствует токен')
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time() - MONTH_AGO)
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework)
                send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
        time.sleep(RETRY_TIME)
        current_timestamp = int(time.time() - RETRY_TIME)


if __name__ == '__main__':
    main()
