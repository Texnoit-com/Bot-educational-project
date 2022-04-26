"""Модуль обработки состояние домашних заданий."""
import logging
import os
import time

import requests
from dotenv import load_dotenv
from telegram import Bot, TelegramError

load_dotenv()
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

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s'
    )
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


class Error200(Exception):
    """Класс ошибки ответа сервера."""

    pass


class HomeworksError(Exception):
    """Класс ошибки."""

    pass


class StatusError(Exception):
    """Класс ошибки."""

    pass


def send_message(bot: Bot, message: str) -> None:
    """Формирование сообщения для бота."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Сообщение успешно отправленно: {message}')
    except TelegramError as error:
        logger.error(f'Сообщение не оптправленно: {error}')


def get_api_answer(current_timestamp: int) -> dict:
    """Получения данных по API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': 1549962000} #1549962000
    try:
        response = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params=params)
        if response.status_code != 200:
            logger.error('Страница недоступна')
            raise Error200()
        return response.json()
    except requests.exceptions.RequestException as request_error:
        logger.error(f'Ошиюка запроса {request_error}')


def check_response(response: dict):
    """Проверка ответа API на корректность."""
    if response.get('homeworks') is None:
        logger.error('Нет объекта homeworks')
        raise HomeworksError()
    if response.get('homeworks') == []:
        return {}
    if response.get('homeworks')[0].get('status') in HOMEWORK_STATUSES:
        return response.get('homeworks')[0]
    else:
        logger.error('Неопределенный статус')
        raise StatusError()


def parse_status(homework: dict) -> str:
    """Парсинг ответа на запрос."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None:
        logger.error('Пустое сообщение имени работы')
        return 'В данный момент работа не сформированна'
    if homework_status is None:
        logger.error('Пустое сообщение статуса')
        return f'В данный момент статус {homework_name} определяется'
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Проверка наличия токенов."""
    if PRACTICUM_TOKEN is None:
        logger.critical('Отсутствует PRACTICUM_TOKEN')
        return False
    if TELEGRAM_TOKEN is None:
        logger.critical('Отсутствует TELEGRAM_TOKEN')
        return False
    if TELEGRAM_CHAT_ID is None:
        logger.critical('Отсутствует TELEGRAM_CHAT_ID')
        return False
    return True


def main() -> None:
    """Основная логика работы бота."""
    if not check_tokens():
        exit()
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks)
                send_message(bot, message)
                time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.critical(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
