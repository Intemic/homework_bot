import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv
from telegram.error import TelegramError

from exceptions import (ErrorConnection, ErrorEnv, ErrorResponseData,
                        ErrorStatus)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    ('%(asctime)s - %(name)s - %(levelname)s '
     '-%(funcName)s - %(lineno)d - %(message)s')
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


def check_tokens():
    """Проверим определены ли все необходимые переменные."""
    variables = []

    if PRACTICUM_TOKEN is None or not PRACTICUM_TOKEN:
        variables.append('PRACTICUM_TOKEN')

    if TELEGRAM_TOKEN is None or not TELEGRAM_TOKEN:
        variables.append('TELEGRAM_TOKEN')

    if TELEGRAM_CHAT_ID is None or not TELEGRAM_CHAT_ID:
        variables.append('TELEGRAM_CHAT_ID')

    if variables:
        message = 'Не определена(ы) переменная(ые): ' + ', '.join(variables)
        raise ErrorEnv(message)


def send_message(bot: telegram.Bot, message: str):
    """Отправка сообщения."""
    try:
        logger.debug('Пытаемся отправить сообщение: ' + message)
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('отправлено сообщение :' + message)
    except TelegramError as error:
        logger.error(error)


def get_api_answer(timestamp: int) -> dict:
    """Получаем данные от сервера."""
    payload = {'from_date': timestamp}

    url_info = f'{ENDPOINT}, параметры: {payload}'

    try:
        logger.debug(f'Пытаемся отправить запрос на адрес: {url_info}')
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        logger.debug(f'Результат запроса с адреса: {url_info}'
                     f' - {response.status_code}')
        if response.status_code != HTTPStatus.OK:
            raise ValueError('Ошибка подключения')
    except ValueError:
        raise ErrorConnection(f'Неверный статус ответа при подключении к узлу:'
                              f'{url_info}, статус: {response.status_code}')
    except requests.RequestException:
        raise ErrorConnection(f'Ошибка подключения к узлу: {url_info}')

    return response.json()


def check_response(response: dict):
    """Проверяем соответствие ответа сервера типу данных."""
    logger.debug('Начало проверки данных')

    parameters = []
    if not isinstance(response, dict):
        raise ErrorResponseData('Не коректный ответа сервера, '
                                'результат не словарь')

    home_works = response.get('homeworks')
    if home_works is None:
        parameters.append('homeworks')
    if not isinstance(home_works, list):
        raise ErrorResponseData('Не коректный ответа сервера, '
                                '"homeworks" не list')

    if response.get('current_date') is None:
        parameters.append('current_date')

    if parameters:
        message = ('Не корректный ответ сервера, '
                   'отсутствую параметр(ы): '
                   + ', '.join(parameters))
        raise ErrorResponseData(message)

    logger.debug('Данные от сервера проверены успешно')


def parse_status(homework) -> str:
    """Считываем статус работы."""
    logger.debug('Начинаем разбор состояния домашнего задания')

    parameters = []
    homework_name = homework.get('homework_name')
    if homework_name is None:
        parameters.append('homework_name')

    status = homework.get('status')
    if status is None:
        parameters.append('status')

    if parameters:
        message = ('В структуре отсутствуют параметр(ы): '
                   + ', '.join(parameters))
        raise ErrorResponseData(message)

    try:
        verdict = HOMEWORK_VERDICTS[status]
    except KeyError:
        raise ErrorStatus(f'Не корректный статус работы: {status}')

    logger.debug('Разбор состояния домашнего задания успешен')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    last_error = ''

    try:
        check_tokens()
    except ErrorEnv as error:
        logger.critical(error)
        sys.exit(1)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            answer = get_api_answer(timestamp)
            check_response(answer)
            works = answer.get('homeworks')
            if works:
                text_status = parse_status(works[0])
                send_message(bot, text_status)
            else:
                logger.debug('Отсутствуют новые статусы')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message, exc_info=True)
            if message != last_error:
                last_error = message
                send_message(bot, message)

        timestamp = int(time.time())
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
