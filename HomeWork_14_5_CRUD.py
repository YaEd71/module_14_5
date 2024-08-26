import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from crud_functions import initiate_db, get_all_products, add_user, is_included

API_TOKEN = '--'

# Создаем экземпляр бота
bot = Bot(token=API_TOKEN)

# Создаем диспетчер с хранилищем состояний в памяти
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Инициализируем базу данных
initiate_db()

# Получаем все продукты из базы данных
products = get_all_products()

# Определяем группу состояний
class UserState(StatesGroup):
    age = State()
    growth = State()
    weight = State()

# Новый класс состояний для регистрации
class RegistrationState(StatesGroup):
    username = State()
    email = State()
    age = State()
    balance = State()

# Создаем обычную клавиатуру
keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
keyboard.add(KeyboardButton('Рассчитать'), KeyboardButton('Информация'),
             KeyboardButton('Купить'), KeyboardButton('Регистрация'))

# Это код остается без изменений
# Создаем Inline клавиатуру для основного меню
inline_kb = InlineKeyboardMarkup(row_width=1)
inline_kb.add(InlineKeyboardButton(text='Рассчитать норму калорий', callback_data='calories'))
inline_kb.add(InlineKeyboardButton(text='Формулы расчёта', callback_data='formulas'))

# Создаем Inline клавиатуру для покупки продуктов
buying_kb = InlineKeyboardMarkup(row_width=2)
buying_kb.add(
    InlineKeyboardButton(text="Product1", callback_data="product_buying"),
    InlineKeyboardButton(text="Product2", callback_data="product_buying"),
    InlineKeyboardButton(text="Product3", callback_data="product_buying"),
    InlineKeyboardButton(text="Product4", callback_data="product_buying")
)

# Функция, обрабатывающая команду /start
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply(
        'Привет! Я бот, помогающий твоему здоровью.\nНажмите "Рассчитать", чтобы начать расчет нормы калорий.\n'
        'Нажмите "Купить", чтобы купить витамины',
        reply_markup=keyboard
    )

# Функция для отображения Inline меню
@dp.message_handler(lambda message: message.text == 'Рассчитать')
async def main_menu(message: types.Message):
    await message.reply('Выберите опцию:', reply_markup=inline_kb)

# Функция для отображения формул
@dp.callback_query_handler(lambda c: c.data == 'formulas')
async def get_formulas(call: types.CallbackQuery):
    formula_text = ("Формула Миффлина-Сан Жеора для расчета нормы калорий:\n\n"
                    "Для мужчин: (10 * вес (кг)) + (6.25 * рост (см)) - (5 * возраст) + 5\n"
                    "Для женщин: (10 * вес (кг)) + (6.25 * рост (см)) - (5 * возраст) - 161")
    await call.message.answer(formula_text)
    await call.answer()

# Функция для установки возраста
@dp.callback_query_handler(lambda c: c.data == 'calories', state=None)
async def set_age(call: types.CallbackQuery):
    await call.message.answer('Введите свой возраст:')
    await UserState.age.set()
    await call.answer()

# Функция для установки роста
@dp.message_handler(state=UserState.age)
async def set_growth(message: types.Message, state: FSMContext):
    await state.update_data(age=message.text)
    await message.reply('Введите свой рост (в см):')
    await UserState.growth.set()

# Функция для установки веса
@dp.message_handler(state=UserState.growth)
async def set_weight(message: types.Message, state: FSMContext):
    await state.update_data(growth=message.text)
    await message.reply('Введите свой вес (в кг):')
    await UserState.weight.set()

# Функция для расчета и отправки нормы калорий
@dp.message_handler(state=UserState.weight)
async def send_calories(message: types.Message, state: FSMContext):
    await state.update_data(weight=message.text)

    data = await state.get_data()

    try:
        age = int(data['age'])
        growth = int(data['growth'])
        weight = int(data['weight'])

        calories = int(10 * weight + 6.25 * growth - 5 * age + 5)

        await message.reply(f"Ваша норма калорий: {calories} ккал в день", reply_markup=keyboard)
    except ValueError:
        await message.reply("Ошибка в введенных данных. Пожалуйста, убедитесь, что вы ввели числовые значения.",
                            reply_markup=keyboard)

    await state.finish()

# Функцию для отображения списка продуктов
@dp.message_handler(lambda message: message.text == 'Купить')
async def get_buying_list(message: types.Message):
    global products
    products = get_all_products()  # Обновляем список продуктов

    for product in products:
        await message.answer(f"Название: {product[1]} | Описание: {product[2]} | Цена: {product[3]}")
        with open(f"files/Фото_{product[0]}.png", 'rb') as photo:
            await message.answer_photo(photo)

    # Создаем новую Inline клавиатуру на основе полученных продуктов
    buying_kb = InlineKeyboardMarkup(row_width=2)
    for product in products:
        buying_kb.add(InlineKeyboardButton(text=product[1], callback_data=f"product_buying_{product[0]}"))

    await message.answer("Выберите продукт для покупки:", reply_markup=buying_kb)


# Функцию для подтверждения покупки
@dp.callback_query_handler(lambda c: c.data.startswith('product_buying_'))
async def send_confirm_message(call: types.CallbackQuery):
    product_id = int(call.data.split('_')[-1])
    product = next((p for p in products if p[0] == product_id), None)
    if product:
        await call.message.answer(f"Вы успешно приобрели продукт: {product[1]}!")
    else:
        await call.message.answer("Извините, произошла ошибка при покупке продукта.")
    await call.answer()


# Новые функции для регистрации

@dp.message_handler(lambda message: message.text == 'Регистрация', state=None)
async def sign_up(message: types.Message):
    await message.reply("Введите имя пользователя (только латинский алфавит):")
    await RegistrationState.username.set()

@dp.message_handler(state=RegistrationState.username)
async def set_username(message: types.Message, state: FSMContext):
    if not is_included(message.text):
        await state.update_data(username=message.text)
        await message.reply("Введите свой email:")
        await RegistrationState.email.set()
    else:
        await message.reply("Пользователь существует, введите другое имя")
        await RegistrationState.username.set()

@dp.message_handler(state=RegistrationState.email)
async def set_email(message: types.Message, state: FSMContext):
    await state.update_data(email=message.text)
    await message.reply("Введите свой возраст:")
    await RegistrationState.age.set()

@dp.message_handler(state=RegistrationState.age)
async def set_age(message: types.Message, state: FSMContext):
    await state.update_data(age=message.text)
    user_data = await state.get_data()
    add_user(user_data['username'], user_data['email'], int(user_data['age']))
    await message.reply(f"Регистрация завершена! Ваш баланс: 1000", reply_markup=keyboard)
    await state.finish()

# Oстается без изменений
# Функция, обрабатывающая все остальные сообщения
@dp.message_handler()
async def all_messages(message: types.Message):
    if message.text == 'Информация':
        await message.reply('Этот бот поможет вам рассчитать норму калорий. Нажмите "Рассчитать", чтобы начать.',
                            reply_markup=keyboard)
    else:
        await message.reply(
            'Введите команду /start, чтобы начать общение или нажмите "Рассчитать" для расчета нормы калорий.',
            reply_markup=keyboard)

if __name__ == '__main__':
    # Запуск бота
    executor.start_polling(dp, skip_updates=True)