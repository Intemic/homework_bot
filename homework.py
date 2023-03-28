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
                        ErrorSend, ErrorStatus)

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
        raise ErrorSend('Не удалось отправить сообщение: ' + message)


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
    except requests.RequestException:
        raise ErrorConnection(f'Ошибка подключения к узлу: {url_info}')
    except Exception:
        raise ErrorConnection(f'Ошибка подключения к узлу: {url_info}')

    return response.json()


def check_response(response: dict):
    """Проверяем соответствие ответа сервера типу данных."""
    if not type(response) is dict:
        raise ErrorResponseData()

    home_works = response.get('homeworks')
    if home_works is None or not type(home_works) is list:
        raise ErrorResponseData()

    if response.get('current_date') is None:
        raise ErrorResponseData()

    if len(home_works) > 0:
        if home_works[0].get('status') is None:
            raise ErrorResponseData()
        if home_works[0].get('homework_name') is None:
            raise ErrorResponseData()


def parse_status(homework) -> str:
    """Считываем статус работы."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise ErrorResponseData()

    try:
        status = homework.get('status')
        if status is None:
            logger.debug(homework)
        else:
            verdict = HOMEWORK_VERDICTS[status]
    except KeyError:
        raise ErrorStatus('Не корректный статус работы')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    error_list = set()

    try:
        check_tokens()
    except ErrorEnv as error:
        logger.critical(error)
        return None

    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    while True:
        timestamp = int(time.time())
        try:
            answer = get_api_answer(timestamp)
            check_response(answer)
            for work in answer.get('homeworks'):
                text_status = parse_status(work)
                send_message(bot, text_status)

        # здесь уже ничего не сделать
        except ErrorSend:
            pass

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message not in error_list:
                error_list.add(message)
                send_message(bot, message)

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
