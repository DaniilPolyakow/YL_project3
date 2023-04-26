from functions import *


# Определяем функцию-обработчик сообщений.
# У неё два параметра, updater, принявший сообщение и контекст -
# дополнительная информация о сообщении.
async def find_place(update, context):
    global current_city
    global current_coordinates
    # У объекта класса Updater есть поле message,
    # являющееся объектом сообщения.
    # У message есть поле text, содержащее текст полученного сообщения,
    # а также метод reply_text(str),
    # отсылающий ответ пользователю, от которого получено сообщение.
    await geocoder(update, context)
    current_city = update.message.text
    await save_request(current_city)


# Нахождение географического объекта на карте по названию
# Определение координат объекта
async def geocoder(update, context):
    global current_coordinates
    geocoder_uri = "http://geocode-maps.yandex.ru/1.x/"
    response = await get_response(geocoder_uri, params={
        "apikey": API_KEY,
        "format": "json",
        "geocode": update.message.text
    })

    toponym = response["response"]["GeoObjectCollection"][
        "featureMember"][0]["GeoObject"]
    address = toponym['metaDataProperty']['GeocoderMetaData']['text']
    toponym_coordinates = toponym["Point"]["pos"]

    current_coordinates = ",".join(toponym_coordinates.split())

    toponym_longitude, toponym_lattitude = toponym_coordinates.split(",")
    spn = get_ll_spn(0.5)
    ll = ",".join([toponym_longitude, toponym_lattitude])
    # Можно воспользоваться готовой функцией,
    # которую предлагалось сделать на уроках, посвящённых HTTP-геокодеру.
    spn = ",".join(map(str, spn))

    static_api_request = f"http://static-maps.yandex.ru/1.x/?ll={ll}&spn={spn}&l=map"
    await context.bot.send_photo(
        update.message.chat_id,  # Идентификатор чата. Куда посылать картинку.
        # Ссылка на static API, по сути, ссылка на картинку.
        # Телеграму можно передать прямо её, не скачивая предварительно карту.
        static_api_request,
        caption="Нашёл:"
    )


# В этой функции задаются основные команды бота
# Добавляются обработчики и запускается сам бот
def main():
    # Создаём объект Application.
    # Вместо слова "TOKEN" надо разместить полученный от @BotFather токен
    application = Application.builder().token(BOT_TOKEN).build()

    # Создаём обработчик сообщений типа filters.TEXT
    # из описанной выше асинхронной функции echo()
    # После регистрации обработчика в приложении
    # эта асинхронная функция будет вызываться при получении сообщения
    # с типом "текст", т. е. текстовых сообщений.
    text_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, find_place)

    # Регистрируем обработчик в приложении.
    application.add_handler(text_handler)

    # Запускаем приложение.

    # Зарегистрируем их в приложении перед
    # регистрацией обработчика текстовых сообщений.
    # Первым параметром конструктора CommandHandler является название команды.
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("city", city_command))
    application.add_handler(CommandHandler("country", country_command))
    application.add_handler(CommandHandler("temperature", temperature_command))
    application.add_handler(CommandHandler("time", time_command))
    application.add_handler(CommandHandler("cafe", cafe_command))
    application.add_handler(CommandHandler("hotel", hotel_command))
    application.add_handler(CommandHandler("landmarks", landmarks_command))
    application.add_handler(CommandHandler("airport", airport_command))

    application.run_polling()


# Функции - обработчики команд для бота.
# Их сигнатура и поведение аналогичны обработчикам текстовых сообщений.


# Начало работы с новым пользователем
async def start(update, context):
    """Отправляет сообщение когда получена команда /start"""
    user = update.effective_user
    await update.message.reply_html(
        rf"Привет, {user.mention_html()}! Я бот для путешественников. Я помогу Вам найти информацию про место отдыха!",
        reply_markup=markup
    )


# Руководство по работе с ботом для пользователя и описание всех команд
async def help_command(update, context):
    """Отправляет сообщение когда получена команда /help"""
    await update.message.reply_text(
        "Ведите город - место отдыха. После этого я смогу Вам предложить отели, "
        "рестораны, достопримечательности этого города. Расскажу про погоду и другие "
        "особенноси этого места.\n"
        "/start - начало работы с ботом.\n"
        "/help - помощь по работе с ботом.\n"
        "/reset - сброс выбранного города до прошлого запроса.\n"
        "/city - узнать текущий город.\n"
        "/country - узнать текущую страну.\n"
        "/temperature - узнать прогноз погоды в выбранном городе.\n"
        "/time - узнать часовой пояс.\n"
        "/cafe - найти 5 кафе в городе.\n"
        "/hotel - найти 5 ближайших к центру города отелей.\n"
        "/landmarks - найти 10 достопримечательностей.\n"
        "/airport - найти ближайший к центру города аэропорт.", reply_markup=markup)


# Сброс текущего города. Без выбранного города ни одна команда не будет работать
# После этого автоматически выбирается город из последнего запроса
# Если данному запросу ничего не предшествовало, то город останется не выбранным
# При новом запуске бота текущий город - последний запрос
async def reset_command(update, context):
    """Отправляет сообщение когда получена команда /reset"""
    global current_city
    await delete_request()
    await update.message.reply_text("Выбор города сброшен.", reply_markup=markup)
    if await size_of_requests():
        current_city = await get_request()
        await update.message.reply_text(f"Текущий город установлен по предыдущему запросу.\n"
                                        f"Выбранный город - {current_city}", reply_markup=markup)
    else:
        await update.message.reply_text("Текущий город не выбран.", reply_markup=markup)
        current_city = await get_request()


# Возвращает текущий город.
async def city_command(update, context):
    """Отправляет сообщение когда получена команда /city"""
    if not current_city:
        await update.message.reply_text("Текущий город не выбран", reply_markup=markup)
    else:
        await update.message.reply_text(f"Текущий город: {current_city}", reply_markup=markup)


# Возвращает страну, в которой находится текущий город.
async def country_command(update, context):
    """Отправляет сообщение когда получена команда /country"""
    if not current_city:
        await update.message.reply_text("Текущий город не выбран", reply_markup=markup)
    else:
        country = await find_country(current_city)
        await update.message.reply_text(f"Текущая страна: {country}", reply_markup=markup)


# Возвращает полную сводку температуры в текущем городе на день
async def temperature_command(update, context):
    """Отправляет сообщение когда получена команда /temperature"""
    if not current_city:
        await update.message.reply_text(f"Текущий город не выбран", reply_markup=markup)
    else:
        lat = float(current_coordinates.split(",")[1])
        lng = float(current_coordinates.split(",")[0])
        observation = mgr.weather_at_coords(lat, lng)
        weather = observation.weather.temperature('celsius')
        current_temperature = weather["temp"]
        max_temperature = weather["temp_max"]
        min_temperature = weather["temp_min"]
        perceived_temperature = weather["feels_like"]
        await update.message.reply_text(
            f"Температура в городе {current_city} (в градусах Цельсия):\n"
            f"Текущая - {current_temperature}, ощущается как {perceived_temperature}\n"
            f"Максимальная дневная температура - {max_temperature}\n"
            f"Минимальная дневная температура - {min_temperature}",
            reply_markup=markup)


# Возвращает время в текущем городе, а также сравнивает его со временем в Москве
async def time_command(update, context):
    """Отправляет сообщение когда получена команда /time"""
    if not current_city:
        await update.message.reply_text("Текущий город не выбран", reply_markup=markup)
    else:
        my_timezone = 'Europe/Moscow'
        now = datetime.datetime.now(pytz.timezone(my_timezone))
        now = str(now).split(".")[0]

        tf = TimezoneFinder(in_memory=True)
        longitude = float(str(current_coordinates).split(",")[0])
        latitude = float(str(current_coordinates).split(",")[1])
        timezone = tf.timezone_at(lng=longitude, lat=latitude)

        now_timezone = datetime.datetime.now(pytz.timezone(timezone))
        now_timezone = str(now_timezone).split(".")[0]
        await update.message.reply_text(f"Время в Москве: {now}\n"
                                        f"Время в {current_city}: "
                                        f"{now_timezone}", reply_markup=markup)


# Возвращает 5 случайновыбранных кафе из текущего города
async def cafe_command(update, context):
    """Отправляет сообщение когда получена команда /cafe"""
    if not current_city:
        await update.message.reply_text("Текущий город не выбран", reply_markup=markup)
    else:
        result = await get_cafes(current_coordinates)
        for cafe in result:
            await get_image(update, context, cafe, 0.001)


# Возвращает 5 ближайших к центру отелей из текущего города
async def hotel_command(update, context):
    """Отправляет сообщение когда получена команда /hotel"""
    if not current_city:
        await update.message.reply_text("Текущий город не выбран", reply_markup=markup)
    else:
        result = await get_nearest_hotel(current_coordinates)
        for hotel in result:
            await get_image(update, context, hotel, 0.001)


# Возвращает 10 случайновыбранных достопримечательностей из текущего города
async def landmarks_command(update, context):
    """Отправляет сообщение когда получена команда /landmarks"""
    if not current_city:
        await update.message.reply_text("Текущий город не выбран", reply_markup=markup)
    else:
        result = await get_landmarks(current_coordinates)
        for landmark in result:
            await get_image(update, context, landmark, 0.001)


# Возвращает ближайший к центру города аэропорт
async def airport_command(update, context):
    """Отправляет сообщение когда получена команда /airport"""
    if not current_city:
        await update.message.reply_text("Текущий город не выбран", reply_markup=markup)
    else:
        airport = await get_nearest_airport(current_coordinates)
        await get_image(update, context, airport, 0.1)


# Запускаем функцию main() в случае запуска скрипта.
if __name__ == '__main__':
    # Создание клавиатуры с командами для бота
    reply_keyboard = [['/help', '/reset'],
                      ['/city', '/country'],
                      ['/temperature', '/time'],
                      ['/cafe', '/hotel'],
                      ['/landmarks', '/airport']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)

    main()
