# Подключение всех используемых библиотек

import logging
import aiohttp
import random
import pytz
import datetime
import pyowm
from timezonefinder import TimezoneFinder

# Добавим необходимый объект из модуля telegram.ext

# Импортируем необходимые классы.

from telegram.ext import CommandHandler
from telegram.ext import Application, MessageHandler, filters
from telegram import ReplyKeyboardMarkup

# Импорт всех ключей и идентификаторов

from config import BOT_TOKEN
from config import API_KEY
from config import API_KEY1
from config import API_KEY2

# Запускаем логгирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)


# Сохранение последнего запроса пользователя в текстовый файл
async def save_request(city):
    with open("requests.txt", "a", encoding="utf8") as save_file:
        print(city, file=save_file)


# Удаление последнего запроса пользователя из текстового файла
async def delete_request():
    with open("requests.txt", encoding="utf8") as get_file:
        data = get_file.readlines()
    with open("requests.txt", "w", encoding="utf8") as save_file:
        size = await size_of_requests()
        for line in data[:size - 1]:
            print(line, file=save_file)


# Получение последнего запроса пользователя из текстового файла
# Если файл пуст, то ничего не будет возвращено
async def get_request():
    if await size_of_requests():
        with open("requests.txt", encoding="utf8") as get_file:
            data = get_file.readlines()
            return data[-1]
    else:
        return None


# Возвращение количества сохраненных в текстовом файле запросов пользователя
async def size_of_requests():
    with open("requests.txt", encoding="utf8") as get_file:
        data = get_file.readlines()
        return len(data)


# Установление текущего городапо последнему запросу при новом запуске программы
with open("requests.txt", encoding="utf8") as get_file:
    data = get_file.readlines()
    if len(data):
        current_city = data[-1]
    else:
        current_city = None

current_coordinates = "0,0"
# Использование стороннего API для получения температуры по координатам
owm = pyowm.OWM(API_KEY2)
mgr = owm.weather_manager()


# Вспомогательная функция для получения картинки на карте
def get_ll_spn(long_lat):
    is_valid_spn = False
    while not is_valid_spn:
        longitude = long_lat
        latitude = long_lat
        return longitude, latitude


# Осуществления запросов на сервера
async def get_response(url, params):
    logger.info(f"getting {url}")
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            return await resp.json()


# Определение страны по городу
async def find_country(city):
    geocoder_uri = "http://geocode-maps.yandex.ru/1.x/"
    response = await get_response(geocoder_uri, params={
        "apikey": API_KEY,
        "format": "json",
        "geocode": city
    })

    toponym = response["response"]["GeoObjectCollection"][
        "featureMember"][0]["GeoObject"]
    country = next(filter(lambda x: x['kind'] == 'country',
                          (
                              toponym["metaDataProperty"]["GeocoderMetaData"]['Address'][
                                  'Components'])))
    return country['name']


# Нахождение 5 случайных кафе в выбранном городе
async def get_cafes(coordinates):
    result = []
    numbers = random.sample(range(0, 50, 2), 5)
    for i in range(5):
        search_api_server = "https://search-maps.yandex.ru/v1/"
        api_key = API_KEY1

        address_ll = coordinates

        search_params = {
            "apikey": api_key,
            "text": "кафе",
            "lang": "ru_RU",
            "ll": address_ll,
            "type": "biz",
            "results": 1,
            "skip": numbers[i],
            "format": "json"
        }
        response = await get_response(search_api_server, params=search_params)
        organization = response["features"][0]
        cafe_name = organization["properties"]["CompanyMetaData"]["name"]
        cafe_address = organization["properties"]["CompanyMetaData"]["address"]
        cafe_coordinates = organization["geometry"]["coordinates"]
        result.append({"name": cafe_name, "address": cafe_address, "coordinates": cafe_coordinates})
    return result


# Получение координат объекта
async def get_coordinates():
    geocoder_uri = "http://geocode-maps.yandex.ru/1.x/"
    response = await get_response(geocoder_uri, params={
        "apikey": API_KEY,
        "format": "json",
        "geocode": current_city
    })

    toponym = response["response"]["GeoObjectCollection"][
        "featureMember"][0]["GeoObject"]
    toponym_coodrinates = toponym["Point"]["pos"]
    return list(map(float, toponym_coodrinates.split()))


# Нахождение 5 ближайших к центру отелей в выбранном городе
async def get_nearest_hotel(coordinates):
    result = []
    for i in range(5):
        search_api_server = "https://search-maps.yandex.ru/v1/"
        api_key = API_KEY1

        address_ll = coordinates

        search_params = {
            "apikey": api_key,
            "text": "отель",
            "lang": "ru_RU",
            "ll": address_ll,
            "type": "biz",
            "results": 1,
            "skip": i,
            "format": "json"
        }
        response = await get_response(search_api_server, params=search_params)
        organization = response["features"][0]
        hotel_name = organization["properties"]["CompanyMetaData"]["name"]
        hotel_address = organization["properties"]["CompanyMetaData"]["address"]
        hotel_coordinates = organization["geometry"]["coordinates"]
        result.append(
            {"name": hotel_name, "address": hotel_address, "coordinates": hotel_coordinates})
    return result


# Получение изображения объекта на карте
async def get_image(update, context, object, long_lat):
    coordinates = object['coordinates']
    address = object['address']
    toponym_longitude, toponym_lattitude = coordinates
    spn = get_ll_spn(long_lat)
    ll = ",".join(list(map(str, [toponym_longitude, toponym_lattitude])))
    # Можно воспользоваться готовой функцией,
    # которую предлагалось сделать на уроках, посвящённых HTTP-геокодеру.
    spn = ",".join(map(str, spn))

    static_api_request = f"http://static-maps.yandex.ru/1.x/?ll={ll}&spn={spn}&l=map"
    await context.bot.send_photo(
        update.message.chat_id,  # Идентификатор чата. Куда посылать картинку.
        # Ссылка на static API, по сути, ссылка на картинку.
        # Телеграму можно передать прямо её, не скачивая предварительно карту.
        static_api_request,
        caption=f"Объект: {object['name']}, адрес: {address}"
    )


# Получение 10 случайных достопримечательностей в выбранном городе
async def get_landmarks(coordinates):
    result = []
    numbers = random.sample(range(0, 100, 2), 10)
    for i in range(10):
        search_api_server = "https://search-maps.yandex.ru/v1/"
        api_key = API_KEY1

        address_ll = coordinates

        search_params = {
            "apikey": api_key,
            "text": "достопримечательности",
            "lang": "ru_RU",
            "ll": address_ll,
            "type": "biz",
            "results": 1,
            "skip": numbers[i],
            "format": "json"
        }
        response = await get_response(search_api_server, params=search_params)
        organization = response["features"][0]
        landmark_name = organization["properties"]["CompanyMetaData"]["name"]
        landmark_address = organization["properties"]["CompanyMetaData"]["address"]
        landmark_coordinates = organization["geometry"]["coordinates"]
        result.append({"name": landmark_name, "address": landmark_address,
                       "coordinates": landmark_coordinates})
    return result


# Получение блжайшего к городу аэропорта
async def get_nearest_airport(coordinates):
    search_api_server = "https://search-maps.yandex.ru/v1/"
    api_key = API_KEY1

    address_ll = coordinates

    search_params = {
        "apikey": api_key,
        "text": "аэропорт",
        "lang": "ru_RU",
        "ll": address_ll,
        "type": "biz",
        "format": "json"
    }
    response = await get_response(search_api_server, params=search_params)
    organization = response["features"][0]
    airport_name = organization["properties"]["CompanyMetaData"]["name"]
    airport_address = organization["properties"]["CompanyMetaData"]["address"]
    airport_coordinates = organization["geometry"]["coordinates"]
    return {"name": airport_name, "address": airport_address, "coordinates": airport_coordinates}
