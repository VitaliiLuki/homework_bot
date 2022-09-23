import logging
import os
import sys
import time
from http import HTTPStatus
import exceptions
import requests
import telegram
from dotenv import load_dotenv


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_SECRET_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_SECRET_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_SECRET_ID')
ONE_WEEK_BEFORE_CURRENT_TIME = 604800
RETRY_TIME = 5

ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_response(response):
    """Проверка типов, длинны и наличия необходимых значений ответа от API."""
    if not isinstance(response, dict):
        raise TypeError('Ответ от API содержит неверный тип данных.')
    if not response:
        raise ValueError('Ответ от API содержит пустой словарь')
    if 'homeworks' not in response:
        raise KeyError('Ответ от API не содержит ключа "homeworks".')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError(
            'Значения по ключу "homeworks" не соответствуют типу "list".'
        )
    logging.info('Проверка наличия ключа "homeworks" прошла успешно.')
    return response.get('homeworks')


def check_tokens():
    """Проверка наличия необходимых переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def get_api_answer(current_timestamp):
    """Получение данных от эндпоинта в python-читаемом формате."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(
        url=ENDPOINT,
        headers=HEADERS,
        params=params,
    )
    if response.status_code != HTTPStatus.OK:
        raise ConnectionError(
            f'{response.status_code}: нет доcтупа к эндпоинту.'
        )
    logging.info('Получен ответ от эндпоинта.')
    return response.json()


def parse_status(homework):
    """Извлечение информации о статусе проверки и названии домашней работы."""
    if not isinstance(homework, dict):
        raise TypeError('homework не является словарем!')
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise KeyError('У homework нет имени')
    homework_status = homework.get('status')
    if homework_status is None:
        raise KeyError('У homework нет статуса')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        raise KeyError(f'Ошибка статуса homework : {verdict}')
    logging.info(f'Новый статус {verdict}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot, message):
    """Отправка сообщения пользователю телеграм с определенным "chat_id"."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.info('Сообщение отправлено!')
    except telegram.error.TelegramError as error:
        raise exceptions.NotSendMessageError(f'Ошибка отправки сообщения: {error}')


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time() - ONE_WEEK_BEFORE_CURRENT_TIME)
    if check_tokens() is False:
        logging.critical('Отсутствует один или несколько токенов!')
        sys.exit(0)
    previous_message = ''
    error_message = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework[0])
                if previous_message != message:
                    send_message(bot, message)
                    previous_message = message
                    logging.info('Обновлен статус проверки работы')
                else:
                    logging.info('Статус проверки работы не изменился.')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if error_message != message:
                logging.error(
                    f'При попытке отправки сообщения возникла ошибка - {error}'
                )
                send_message(bot, message)
                error_message = message
            else:
                logging.error(
                    f'Ошибка при повторной отправке сообщения: {error}'
                )
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename='main.log',
        filemode='w',
        format='%(asctime)s, %(levelname)s, %(message)s,'
        '%(name)s, %(funcName)s ,%(lineno)s'
    )

    main()
