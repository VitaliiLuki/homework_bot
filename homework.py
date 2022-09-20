import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
)

logging.debug('Запуск программы')
logging.info('Небходимая информация')
logging.warning('Большая нагрузка!')
logging.error('Бот не смог отправить сообщение')
logging.critical('Критическая ошибка!')


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_SECRET_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_SECRET_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_SECRET_ID')
TEST_TWO_WEEKS_TIME = 1209600
RETRY_TIME = 600

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
    if len(response) == 0:
        raise ValueError('Ответ от API содержит пустой словарь')
    if 'homeworks' in response:
        if not isinstance(response.get('homeworks'), list):
            raise TypeError(
                'Значения по ключу "homeworks" не соответствуют типу "list".'
            )
        logging.info('Проверка наличия ключа "homeworks" прошла успешно.')
        return response.get('homeworks')
    logging.error('Ответ от API не содержит ключа "homeworks".')
    raise KeyError('Ответ от API не содержит ключа "homeworks".')


def check_tokens():
    """Проверка наличия необходимых переменных окружения."""
    if not (PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID):
        return False
    return True


def get_api_answer(current_timestamp):
    """Получение данных от эндпоинта в python-читаемом формате."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(
        url=ENDPOINT,
        headers=HEADERS,
        params=params,
    )
    if response.status_code == HTTPStatus.OK:
        logging.info('Получен ответ от эндпоинта.')
        return response.json()
    else:
        logging.error(f'Эндпоинт: {ENDPOINT} не доступен.')
        raise ConnectionError(
            f'{response.status_code}: нет доcтупа к эндпоинту.'
        )


def parse_status(homework):
    """Извлечение информации о статусе проверки и названии домашней работы."""
    if not isinstance(homework, dict):
        logging.error('homework не является словарем!')
        raise TypeError('homework не является словарем!')
    homework_name = homework.get('homework_name')
    if homework_name is None:
        logging.error('У homework нет имени')
        raise KeyError('У homework нет имени')
    homework_status = homework.get('status')
    if homework_status is None:
        logging.error('У homework нет статуса')
        raise KeyError('У homework нет статуса')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        logging.error(f'Ошибка статуса homework: {verdict}')
        raise KeyError(f'Ошибка статуса homework : {verdict}')
    logging.info(f'Новый статус {verdict}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot, message):
    """Отправка сообщения пользователю телеграм с определенным "chat_id"."""
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if check_tokens() is False:
        logging.critical('Отсутствует один или несколько токенов!')
        message = 'Отсутствует один или несколько токенов для запуска бота.'
        raise SystemError('Работа бота остановлена!')
    else:
        logging.info('Проверка токенов прошла успешно.')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if len(homework) != 0:
                message = parse_status(homework[0])
                send_message(bot, message)
                logging.info('Обновлен статус проверки работы')
            else:
                logging.info('Статус проверки работы не изменился')
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(
                f'При попытке отправки сообщения возникла ошибка - {error}'
            )
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
