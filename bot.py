import requests
import json
import time
import cv2
import numpy as np
import dlib
import os
import face_recognition
import io
import shutil

# Замените "YOUR_BOT_TOKEN" на токен вашего бота, полученного от BotFather
TOKEN = "6902826036:AAH5JfWSBwzKA9lf45jRZObuNig0g6BBRRk"

# Базовый URL для API Telegram
BASE_URL = f"https://api.telegram.org/bot{TOKEN}/"

# Словарь для хранения выбранного языка
user_languages = {}

# Словарь для хранения профилей пользователей
user_profiles = {}

# Словарь для хранения состояний пользователей
user_states = {}

# Доступные языки с флагами
LANGUAGES = {
    "en": "🇺🇸 English",
    "ru": "🇷🇺 Русский",
    "uz": "🇺🇿 O'zbekcha",
}

def reset_profile(chat_id):
    # Удаляем профиль из папки profiles
    profile_path = f"profiles/{chat_id}.json"
    if os.path.exists(profile_path):
        os.remove(profile_path)

    # Удаляем все фотографии из папки downloads
    downloads_path = "downloads"
    user_photos = user_profiles.get(chat_id, {}).get("media", [])
    for media_file_id in user_photos:
        photo_path = f"{downloads_path}/{media_file_id}.jpg"
        video_path = f"{downloads_path}/{media_file_id}.mp4"
        
        if os.path.exists(photo_path):
            os.remove(photo_path)
        if os.path.exists(video_path):
            os.remove(video_path)

    
    
    if chat_id in user_profiles:
        user_profiles[chat_id] = {}


# Отправка текстового сообщения
def send_message(chat_id, text, reply_markup=None):
    url = BASE_URL + "sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": reply_markup
    }
    response = requests.post(url, data=data)
    return response.json()

# Обработка команды /start
def start(chat_id):
    text = "Выберите язык:"
    send_message(chat_id, text, create_language_keyboard())
    user_states[chat_id] = "SELECT_LANGUAGE"

# Создание клавиатуры с кнопками выбора языка
def create_language_keyboard():
    languages = list(LANGUAGES.keys())
    keyboard = {
        "keyboard": [],
        "one_time_keyboard": True,
        "resize_keyboard": True  # Добавляем параметр для автоматического изменения размеров кнопок
    }
    row = []
    for lang_code in languages:
        row.append({"text": LANGUAGES[lang_code]})
        if len(row) == 3:
            keyboard["keyboard"].append(row)
            row = []
    if row:
        keyboard["keyboard"].append(row)
    return json.dumps(keyboard)

# Обработка ответа пользователя на выбор языка
def handle_language_choice(chat_id, language_code):
    if language_code in LANGUAGES:
        user_languages[chat_id] = language_code
        text = "Уже миллионы людей знакомятся в Infinity😍\n\nЯ помогу тебе найти тебе пару или просто друзей👫"
        send_message(chat_id, text, create_start_button())
        user_states[chat_id] = "WAITING_FOR_START"
    else:
        send_message(chat_id, "Invalid language choice. Please choose a valid language.")

def create_start_button():
    keyboard = {
        "keyboard": [["👌 Давай начнем"]],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    return json.dumps(keyboard)

def create_subscribe_keyboard():
    keyboard = {
        "keyboard": [[{"text": "Подписался"}]],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }
    return json.dumps(keyboard)

def handle_start(chat_id, text):
    if text == "👌 Давай начнем" or text == "Заполнить анкету заново":
        subscribed_user_id = chat_id
        if is_user_subscribed(subscribed_user_id):
            handle_ok(chat_id, text)
        else:
            subscribe_text = "Для продолжения, подпишитесь на наш канал:"
            inline_keyboard = [
                [{"text": "Подписаться", "url": "https://t.me/dlyabota77"}]
            ]
            send_message(chat_id, subscribe_text, json.dumps({"inline_keyboard": inline_keyboard}))
            send_message(chat_id, "После подписки нажмите на кнопку 'Подписался'.", create_subscribe_keyboard())
            user_states[chat_id] = "WAITING_FOR_SUBSCRIPTION"
    else:
        text = "Пожалуйста, нажмите '👌 Давай начнем' для продолжения."
        send_message(chat_id, text)

def is_user_subscribed(user_id):
    # Замените YOUR_CHANNEL_USERNAME на username вашего канала
    channel_username = "@dlyabota77"
    
    # Запрос на получение информации о члене канала
    url = f"https://api.telegram.org/bot{TOKEN}/getChatMember"
    params = {"chat_id": channel_username, "user_id": user_id}
    
    response = requests.get(url, params=params)
    data = response.json()
    
    # Проверка статуса членства в канале
    if data["ok"] and data["result"]["status"] == "member":
        return True
    else:
        return False

# Обработка ответа пользователя на "👌 ok" после подтверждения
def handle_ok(chat_id, text):
    if text == "Подписался" or text == "Заполнить анкету заново" or text == "👌 Давай начнем":
        text = "Сколько тебе лет?"
        send_message(chat_id, text)
        user_states[chat_id] = "SELECT_AGE"
    else:
        text = "Пожалуйста, нажмите '👌 Давай начнем' для продолжения."
        send_message(chat_id, text)

def handle_age(chat_id, text):
    if not profile_exists(chat_id):
        user_profiles[chat_id] = {}

    try:
        age = int(text)
        if 10 <= age <= 90:
            # Далее можно обработать возраст
            user_profiles[chat_id]["age"] = age  # Сохранение возраста в профиле пользователя
            save_user_profile(chat_id)  # Сохранение профиля после добавления возраста
            text = "Теперь определимся с полом"
            send_message(chat_id, text, create_gender_keyboard())
            user_states[chat_id] = "SELECT_GENDER"
        else:
            text = "Пожалуйста, введите возраст от 10 до 90 лет:"
            send_message(chat_id, text)
    except ValueError:
        text = "Пожалуйста, введите числовой возраст от 10 до 90 лет:"
        send_message(chat_id, text)


# Создание клавиатуры с кнопками выбора пола
def create_gender_keyboard():
    keyboard = {
        "keyboard": [
            ["Мужчина", "Женщина"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    return json.dumps(keyboard)

# Обработка ответа пользователя на выбор пола
# Обновленный код для обработки выбора пола и кого вы ищете
def handle_gender_choice(chat_id, gender):
    if chat_id not in user_profiles:
        user_profiles[chat_id] = {}  # Создание профиля пользователя при первом обращении
    if user_states[chat_id] == "SELECT_GENDER":
        if gender.lower() == "мужчина" or gender.lower() == "женщина":
            user_profiles[chat_id]["gender"] = gender
            text = "Кого вы ищете?"
            send_message(chat_id, text, create_match_gender_keyboard())
            user_states[chat_id] = "SELECT_MATCH_GENDER"
        else:
            text = "Пожалуйста, выберите ваш пол среди 'Мужчина' или 'Женщина':"
            send_message(chat_id, text)
    else:
        text = "Что-то пошло не так. Пожалуйста, начните снова с команды /start."
        send_message(chat_id, text)

def create_match_gender_keyboard():
    keyboard = {
        "keyboard": [["Девушки", "Парни", "Все равно"]],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    return json.dumps(keyboard)

def handle_match_gender_choice(chat_id, match_gender):
    if user_states.get(chat_id) == "SELECT_MATCH_GENDER":
        if match_gender in ["Девушки", "Парни", "Все равно"]:
            user_profiles[chat_id]["match_gender"] = match_gender
            save_user_profile(chat_id)
            text = "Из какого ты города?"
            send_message(chat_id, text, create_request_location_keyboard())
            user_states[chat_id] = "WAITING_FOR_LOCATION"
        else:
            text = "Пожалуйста, выберите один из вариантов: 'Девушки', 'Парни' или 'Все равно'."
            send_message(chat_id, text)
    else:
        text = "Что-то пошло не так. Пожалуйста, начните снова с команды /start."
        send_message(chat_id, text)

# Добавление функции create_request_location_keyboard
def create_request_location_keyboard():
    keyboard = {
        "remove_keyboard": True
    }
    return json.dumps(keyboard)

# Добавьте этот блок кода в функции handle_location и handle_username перед использованием user_profiles[chat_id]
def handle_location(chat_id, location, first_name):
    if not profile_exists(chat_id):
        user_profiles[chat_id] = {}  # Создание профиля пользователя при первом обращении

    if location is not None:
        user_profiles[chat_id]["location"] = location
        text = f"Как вас называть?"
        send_message(chat_id, text, create_request_username_keyboard(first_name))
        user_states[chat_id] = "SELECT_USERNAME"
    else:
        text = "Ошибка при получении местоположения. Пожалуйста, отправьте ваше местоположение."
        send_message(chat_id, text, create_request_location_keyboard())
    save_user_profile(chat_id)


# Функция для получения информации о пользователе из Telegram
def get_user_info(chat_id):
    url = BASE_URL + "getChatMember"
    params = {"chat_id": chat_id, "user_id": chat_id}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get("result", {})
    return {}

# Эта функция создает клавиатуру с кнопкой "Имя"
def create_request_username_keyboard(first_name):
    keyboard = {
        "keyboard": [[{"text": f"{first_name}"}]],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    return json.dumps(keyboard)

def handle_username(chat_id, text):
    if not profile_exists(chat_id):
        user_profiles[chat_id] = {}  # Создание профиля пользователя при первом обращении

    username = text.strip('@')  # Убираем символ "@" в начале или в конце имени пользователя
    user_profiles[chat_id]["username"] = username
    
    # Сохранение профиля в файл JSON
    save_user_profile(chat_id)
    
    text = "Расскажите о себе:"
    skip_button_keyboard = create_skip_button_keyboard()  # Создаем клавиатуру с кнопкой "Пропустить"
    send_message(chat_id, text, skip_button_keyboard)  # Отправляем текст и клавиатуру
    user_states[chat_id] = "TELL_ABOUT"

def save_user_profile(chat_id):
    profile_path = f"profiles/{chat_id}.json"

    if not os.path.exists("profiles"):
        os.makedirs("profiles")

    existing_profile = load_existing_profile(chat_id)

    try:
        # Обновляем существующий профиль данными из user_profiles[chat_id]
        existing_profile.update(user_profiles[chat_id])

        with open(profile_path, "w", encoding='utf-8') as file:
            json.dump(existing_profile, file, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving profile for {chat_id}: {e}")

def load_existing_profile(chat_id):
    profile_path = f"profiles/{chat_id}.json"

    if os.path.exists(profile_path):
        with open(profile_path, "r", encoding='utf-8') as file:
            return json.load(file)
    else:
        return {}


def create_skip_button_keyboard():
    keyboard = {
        "keyboard": [["Пропустить"]],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    return json.dumps(keyboard)

# Обработка ответа пользователя на ввод информации о себе
def handle_about(chat_id, about):
    if about == "Пропустить":
        text = "Присылайте фото, его будут видеть другие пользователи"
        send_message(chat_id, text)
        user_states[chat_id] = "UPLOAD_MEDIA"
    else:
        user_profiles[chat_id]["about"] = about
        text = "Присылайте фото, его будут видеть другие пользователи"
        user_states[chat_id] = "UPLOAD_MEDIA"
        save_user_profile(chat_id)  # Сохранение профиля после добавления информации о себе
        # Отправляем текст без клавиатуры, чтобы убрать кнопку "Пропустить"
        send_message(chat_id, text)

def handle_media(chat_id, message):
    # В конце удали это
    if chat_id not in user_profiles:
        user_profiles[chat_id] = {}

    if "media" not in user_profiles[chat_id]:
        user_profiles[chat_id]["media"] = []

    user_profiles[chat_id]["media"].append(message["photo"][-1]["file_id"])
    media_count = len(user_profiles[chat_id]["media"])

    if media_count == 1:
        text = "Фото добавлено - 1 из 2. Отправьте еще одну фотографию или сохраните фото"
        send_message(chat_id, text, create_confirm_media_keyboard())
        user_states[chat_id] = "CONFIRM_MEDIA"
    elif media_count == 2:
        text = "Фото добавлено - 2 из 2. Сохраните фото"
        send_message(chat_id, text, create_confirm_media_keyboard())
        user_states[chat_id] = "CONFIRM_MEDIA"  # Изменим состояние на "CONFIRM_MEDIA" после второй фотографии

def profile_exists(chat_id):
    return chat_id in user_profiles and "media" in user_profiles[chat_id]

def create_confirm_media_keyboard():
    keyboard = {
        "keyboard": [["Сохранить фото"]],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    return json.dumps(keyboard)

# Создание клавиатуры с кнопкой подтверждения
def create_confirm_keyboard():
    keyboard = {
        "keyboard": [["Подтвердить"]],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    return json.dumps(keyboard)

# Добавьте функции для загрузки файлов
def download_video_file(file_id):
    file_path = f"downloads/{file_id}.mp4"  # Путь для сохранения видео
    url = BASE_URL + f"getFile?file_id={file_id}"
    response = requests.get(url)
    
    if response.status_code == 200:
        file_info = response.json().get("result", {})
        file_path = f"downloads/{file_id}.mp4"
        file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info['file_path']}"
        video_data = requests.get(file_url).content
        
        with open(file_path, 'wb') as video_file:
            video_file.write(video_data)
            
        return file_path
    else:
        return None

def download_photo_file(file_id):
    file_path = f"downloads/{file_id}.jpg"  # Путь для сохранения фотографии
    url = BASE_URL + f"getFile?file_id={file_id}"
    response = requests.get(url)

    if response.status_code == 200:
        file_info = response.json().get("result", {})
        file_path = f"downloads/{file_id}.jpg"
        file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info['file_path']}"
        photo_data = requests.get(file_url).content

        with open(file_path, 'wb') as photo_file:
            photo_file.write(photo_data)

        return file_path
    else:
        print(f"Ошибка при получении информации о фотографии: {response.status_code}")
        return None

def compare_video_and_photo(chat_id, video_path):
    # Получаем фотографии пользователя
    photos = []
    for photo_file_id in user_profiles[chat_id]["media"]:
        photo_path = download_photo_file(photo_file_id)
        if photo_path:
            photos.append(photo_path)

    # Загрузка видео
    video_capture = cv2.VideoCapture(video_path)
    match_found = False


    # Проверка совпадения лиц для каждой фотографии
    for photo_path in photos:
        # Загрузка фотографии и извлечение лица
        photo = face_recognition.load_image_file(photo_path)
        face_encoding_photo = face_recognition.face_encodings(photo)

        if not face_encoding_photo:
            continue

        # Проверка лиц в каждом кадре видео
        success, frame = video_capture.read()
        while success:
            # Извлечение лиц из кадра видео
            face_locations = face_recognition.face_locations(frame)
            face_encodings = face_recognition.face_encodings(frame, face_locations)

            # Проверка совпадения лиц
            for face_encoding_video in face_encodings:
                matches = face_recognition.compare_faces(face_encoding_photo, face_encoding_video)
                if True in matches:
                    match_found = True
            success, frame = video_capture.read()

    if not match_found:
        text = "Личность не подтверждена."
        buttons_keyboard = {
            "keyboard": [
                ["Повторить", "Пропустить"]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        send_message(chat_id, text, json.dumps(buttons_keyboard))
        user_states[chat_id] = "CONFIRM_IDENTITY"
    else:
        # Если найдено совпадение, отправляем сообщение об успешном подтверждении
        text = "Видеосообщение принято. Личность подтверждена."
        keyboard = {
            "keyboard": [["Готово"]],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        send_message(chat_id, text, json.dumps(keyboard))
        user_states[chat_id] = "WAITING_FOR_CONFIRMATION"


def download_video_file(file_id):
    # Создаем директорию, если её нет
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    file_path = f"downloads/{file_id}.mp4"  # Путь для сохранения видео
    url = BASE_URL + f"getFile?file_id={file_id}"
    response = requests.get(url)

    if response.status_code == 200:
        file_info = response.json().get("result", {})
        file_path = f"downloads/{file_id}.mp4"
        file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info['file_path']}"
        video_data = requests.get(file_url).content

        with open(file_path, 'wb') as video_file:
            video_file.write(video_data)

        return file_path
    else:
        return None

# Функция для отправки фотографии
def send_photo(chat_id, photo_paths, user_data):
    url = BASE_URL + "sendMediaGroup"

    media = []
    for i, path in enumerate(photo_paths):
        media_item = {
            "type": "photo",
            "media": "attach://photo" + str(i),
            "caption": user_data if i == 0 else ""  # Добавляем данные пользователя только к первой фотографии
        }
        media.append(media_item)

    files = {f"photo{i}": (f"photo{i}.jpg", open(path, 'rb')) for i, path in enumerate(photo_paths)}
    data = {
        "chat_id": chat_id,
        "media": json.dumps(media)
    }

    response = requests.post(url, data=data, files=files)
    return response.json()

# Обработка команды /confirm
def confirm(chat_id):
    for photo_file_id in user_profiles[chat_id]["media"]:
        download_photo_file(photo_file_id)
    user_profile = user_profiles.get(chat_id, {})
    user_profile_from_file = load_existing_profile(chat_id)
    user_profile.update(user_profile_from_file)
    user_profiles[chat_id] = user_profile
    username = user_profile.get("username", "")
    age = user_profile.get("age", "")
    location = user_profile.get("location", "")
    identity_status = "Подтверждено✅" if user_profile.get("identity_confirmed", False) else "Не подтверждено❎"
    about = user_profile.get("about", "")

    # Отправка сообщения с данными пользователя
    user_data = f"Имя: {username}\nВозраст: {age}\nМесто проживания: {location}\nЛичность: {identity_status}"

    if about:
        user_data += f"\nО себе: {about}"
    # send_message(chat_id, text)
    photos = user_profile.get("media", [])
    photo_paths = [f"downloads/{photo_file_id}.jpg" for photo_file_id in photos]
    send_photo(chat_id, photo_paths, user_data)

    text = "Все верно?"
    keyboard = {
        "keyboard": [
            ["Заполнить анкету заново"],
            ["Смотреть анкеты"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    send_message(chat_id, text, json.dumps(keyboard))

def create_reaction_keyboard():
    keyboard = {
        "keyboard": [
            ["💙", "⚡", "❌", "😴"],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    return json.dumps(keyboard)

# Обработка обновлений от Telegram
def handle_updates(updates):
    for update in updates:
        if "message" in update:
            chat_id = update["message"]["chat"]["id"]
            message = update["message"]
            first_name = message.get("from", {}).get("first_name", "")
            
            if "location" in message:
                # Это геолокация
                handle_location(chat_id, message["location"], first_name)
            elif "photo" in message:
                # Это фото
                text = message.get("caption")
                handle_media(chat_id, message)
            else:
                text = message.get("text")
                if chat_id not in user_states:
                    start(chat_id)
                elif user_states[chat_id] == "SELECT_LANGUAGE":
                    if text in LANGUAGES.values():
                        lang_code = [k for k, v in LANGUAGES.items() if v == text][0]
                        handle_language_choice(chat_id, lang_code)
                elif user_states[chat_id] == "WAITING_FOR_START":
                    handle_start(chat_id, text)
                elif user_states[chat_id] == "WAITING_FOR_SUBSCRIPTION":
                    if "text" in message:   
                        if message["text"] == "Подписался":
                            subscribed_user_id = message["from"]["id"]
                            if is_user_subscribed(subscribed_user_id):
                                handle_ok(chat_id, text)
                            else:
                                text = "Вы не подписались на наш канал. Пожалуйста, подпишитесь и нажмите 'Подписался'."
                                inline_keyboard = [
                                    [{"text": "Подписаться", "url": "https://t.me/dlyabota77"}]
                                ]
                                send_message(chat_id, text, json.dumps({"inline_keyboard": inline_keyboard}))
                                send_message(chat_id, "После подписки нажмите на кнопку 'Подписался'.", create_subscribe_keyboard())
                elif user_states[chat_id] == "SELECT_AGE":
                    handle_age(chat_id, text)
                elif user_states[chat_id] == "SELECT_GENDER":
                    if text in ["Мужчина", "Женщина"]:
                        handle_gender_choice(chat_id, text)
                elif user_states[chat_id] == "SELECT_MATCH_GENDER":
                    if text in ["Девушки", "Парни", "Все равно"]:
                        handle_match_gender_choice(chat_id, text)
                elif user_states[chat_id] == "WAITING_FOR_LOCATION":
                    handle_location(chat_id, text, first_name)
                elif user_states[chat_id] == "SELECT_USERNAME":
                    handle_username(chat_id, text)
                elif user_states[chat_id] == "TELL_ABOUT":
                    handle_about(chat_id, text)
                elif user_states[chat_id] == "CONFIRM_MEDIA":
                    if text == "Сохранить фото":
                        text = "Хотите подтвердить личность?"
                        keyboard = {
                            "keyboard": [
                                ["Подтвердить", "Пропустить"]
                            ],
                            "resize_keyboard": True,
                            "one_time_keyboard": True
                        }
                        send_message(chat_id, text, json.dumps(keyboard))
                        user_states[chat_id] = "CONFIRM_IDENTITY"
                elif user_states[chat_id] == "CONFIRM_IDENTITY":
                    if text == "Подтвердить":
                        text = "Отправьте круглое видеосообщение с помощью телеграмм (не более 20 секунд)."
                        send_message(chat_id, text)
                        user_states[chat_id] = "RECORDING_VIDEO"
                        user_profiles[chat_id]["video_start_time"] = time.time()
                    elif text == "Пропустить":
                        confirm(chat_id)
                        user_states[chat_id] = "RESET_PROFILE_OPTIONS"
                    elif text == "Повторить":
                        text = "Повторно отправьте круглое видеосообщение с помощью телеграмм (не более 20 секунд)."
                        send_message(chat_id, text)
                        user_states[chat_id] = "RECORDING_VIDEO"
                        user_profiles[chat_id]["video_start_time"] = time.time()
                elif user_states[chat_id] == "RECORDING_VIDEO":
                    file_path = None
                    if "video_note" in message:
                        video_file_id = message["video_note"]["file_id"]
                        video_duration = message["video_note"]["duration"]
                        if video_duration > 20:
                            text = "Длительность видео превышает 20 секунд."
                            keyboard = {
                                "keyboard": [
                                    ["Повторить", "Пропустить"]
                                ],
                                "resize_keyboard": True,
                                "one_time_keyboard": True
                            }
                            send_message(chat_id, text, json.dumps(keyboard))
                            user_states[chat_id] = "CONFIRM_IDENTITY"
                        else:
                            file_path = download_video_file(video_file_id)
                        if file_path:
                            text = "Процесс подтверждения может занять 2-3 минуты. Подождите, пожалуйста..."
                            send_message(chat_id, text)
                            photo_file_id = user_profiles[chat_id]["media"][0]
                            photo_path = download_photo_file(photo_file_id)
                            
                            if photo_path:
                                compare_video_and_photo(chat_id, file_path)
                        
                elif user_states[chat_id] == "WAITING_FOR_CONFIRMATION":
                    if text == "Готово":
                        user_profiles[chat_id]["identity_confirmed"] = True
                        confirm(chat_id)
                        # Очистка профиля пользователя
                        user_profiles[chat_id] = {}
                        user_states[chat_id] = None
                        user_states[chat_id] = "RESET_PROFILE_OPTIONS"
                elif user_states[chat_id] == "RESET_PROFILE_OPTIONS":
                    if text == "Заполнить анкету заново":
                        # Сброс профиля
                        reset_profile(chat_id)
                        subscribed_user_id = update["message"]["from"]["id"]
                        if is_user_subscribed(subscribed_user_id):
                            handle_ok(chat_id, text)
                        else:
                            handle_start(chat_id, text)

                        # Перевод пользователя на начальный этап
                        # start(chat_id)
                    elif text == "Смотреть анкеты":
                        if chat_id in user_profiles:
                            match_gender = user_profiles[chat_id].get("match_gender", "")
                            profiles_to_show = []

                            if match_gender == "Девушки":
                                profiles_to_show = [profile for profile in user_profiles.values() if profile.get("gender") == "Женщина"]
                                send_message(chat_id, "🙍🏻‍♀️🔍", create_reaction_keyboard())
                            elif match_gender == "Парни":
                                profiles_to_show = [profile for profile in user_profiles.values() if profile.get("gender") == "Мужчина"]
                                send_message(chat_id, "🙎🏻‍♂️🔍", create_reaction_keyboard())
                            else:
                                profiles_to_show = [profile for profile in user_profiles.values() if profile.get("gender") in ["Женщина", "Мужчина"]]
                                send_message(chat_id, "🙍🏻‍♀️🙎🏻‍♂️🔍", create_reaction_keyboard())

        # Отправка фотографий и данных пользователей
                            for profile in profiles_to_show:    
                                username = profile.get("username", "")
                                age = profile.get("age", "")
                                location = profile.get("location", "")
                                identity_status = "Подтверждено✅" if profile.get("identity_confirmed", False) else "Не подтверждено❎"
                                about = profile.get("about", "")
            
                                user_data = f"Имя: {username}\nВозраст: {age}\nМесто проживания: {location}\nЛичность: {identity_status}"

                                if about:
                                    user_data += f"\nО себе: {about}"
            
                                photos = profile.get("media", [])
                                photo_paths = [f"downloads/{photo_file_id}.jpg" for photo_file_id in photos]
                                send_photo(chat_id, photo_paths, user_data)
                        else:
                            send_message(chat_id, "Прежде чем смотреть анкеты, заполните свою анкету.")
                    # Обработка просмотра анкет (добавьте соответствующий код)
                        
                    # user_states[chat_id] = None

                # ... (ваш текущий код обработки сообщений)
# Основная функция
def main():
    offset = None
    while True:
        url = BASE_URL + "getUpdates"
        params = {"offset": offset, "timeout": 30}
        response = requests.get(url, params=params)
        updates = response.json().get("result", [])
        
        for update in updates:
            offset = update["update_id"] + 1
            handle_updates([update])


if __name__ == "__main__":
    main()