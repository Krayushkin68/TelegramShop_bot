import asyncio
import json
import logging
import re
from datetime import datetime

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from DB import shop_db
from ExternalAPI.youmoney import YouMoneyPayment
from Keyboards.keyboards import main_kb, account_kb, balance_kb, deposit_kb, back_main_kb, admin_kb, back_main_admin_kb

API_TOKEN = json.load(open('config.json'))['BOT_TOKEN']

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=MemoryStorage())
bot_admin = 440152634

try:
    payer = YouMoneyPayment(bot_url='http://t.me/Andrey_shop_bot')
except Exception as error:
    print(error)
    exit(0)

shop_db.create_tables()


class CustomerStates(StatesGroup):
    categories = State()
    buy_choose = State()
    buy_count = State()
    buy_confirm = State()
    coupon_activation = State()
    deposit_sum = State()
    deposit_wait = State()
    admin = State()
    admin_add_category = State()
    admin_del_category = State()
    admin_add_product = State()
    admin_del_product = State()
    admin_coupon = State()
    admin_txt = State()
    admin_bulk_send = State()


async def check_user(from_user):
    user = shop_db.check_user(user_id=from_user.id)
    if not user:
        if from_user.username:
            username = from_user.username
        elif from_user.first_name:
            username = from_user.first_name
        else:
            username = 'user'
        shop_db.add_user(user=[from_user.id, username])
    else:
        username = user[1]
    return username


@dp.message_handler(commands=['start'], state='*')
@dp.message_handler(Text(equals='↪️Вернуться в главное меню↩️'), state='*')
async def welcome(message: types.Message, state: FSMContext):
    name = await check_user(message.from_user)
    current_state = await state.get_state()
    if current_state is not None:
        # Если он вернулся из раздела покупки с забронированными товарами, то вернуть их в бд
        if current_state == 'CustomerStates:buy_confirm':
            async with state.proxy() as data:
                if data.get('category') and data.get('name') and data.get('price') and data.get('products'):
                    [shop_db.add_product(product=[data['category'], data['name'], data['price'], p[1]]) for p in
                     data['products']]
        await state.finish()

    msg = f"Привет <b>{name}</b>, это Телеграм магазин"
    await bot.send_message(message.from_user.id, msg, reply_markup=main_kb)


# ------------------------------------ Админка ----------------------------------------------------
@dp.message_handler(commands=['admin'], state='*')
async def welcome_admin(message: types.Message):
    if message.from_user.id == bot_admin:
        msg = f"<b>Привет мой любимый админчик</b>"
        await CustomerStates.admin.set()
        await bot.send_message(message.from_user.id, msg, reply_markup=admin_kb)
    else:
        await bot.send_message(message.from_user.id, 'Не лезь куда не надо', reply_markup=main_kb)


@dp.message_handler(Text(equals='К админке'), state=[CustomerStates.admin, CustomerStates.admin_txt,
                                                     CustomerStates.admin_coupon, CustomerStates.admin_add_category,
                                                     CustomerStates.admin_add_product,
                                                     CustomerStates.admin_del_category,
                                                     CustomerStates.admin_del_product, CustomerStates.admin_bulk_send])
async def back_admin(message: types.Message):
    await CustomerStates.admin.set()
    await bot.send_message(message.from_user.id, '<b>Админка</b>', reply_markup=admin_kb)


# Основные команды админки
@dp.message_handler(content_types=types.ContentTypes.TEXT, state=CustomerStates.admin)
async def admin_process(message: types.Message):
    if message.text in ['Добавить категорию', 'Удалить категорию']:
        if message.text == 'Добавить категорию':
            await CustomerStates.admin_add_category.set()
            await message.reply('Введите название категории', reply_markup=back_main_admin_kb)
        else:
            await CustomerStates.admin_del_category.set()
            categories = '\n'.join(shop_db.select_categories())
            await message.reply(f'Введите название одной из категорий:\n{categories}', reply_markup=back_main_admin_kb)
    if message.text in ['Добавить товар', 'Удалить товар']:
        if message.text == 'Добавить товар':
            await CustomerStates.admin_add_product.set()
            info = '[Название товара];[Категория];[Цена];[Содержание]'
            await bot.send_message(message.from_user.id,
                                   f'Введите через точку с запятой параметры товара:\n<b><i>{info}</i></b>',
                                   reply_markup=back_main_admin_kb)
        else:
            await CustomerStates.admin_del_product.set()
            await bot.send_message(message.from_user.id, f'Товары:\n {shop_db.select_all_products()}')
            await bot.send_message(message.from_user.id, 'Введите id товаров через запятую',
                                   reply_markup=back_main_admin_kb)
    if message.text == 'Создать купон':
        await CustomerStates.admin_coupon.set()
        users = shop_db.select_users_pretty()
        await bot.send_message(message.from_user.id, users, reply_markup=back_main_admin_kb)
        await bot.send_message(message.from_user.id,
                               'Введите id пользователя и сумму купона через точку с запятой:\n'
                               '<b><i>[ID пользователя];[Сумма купона]</i></b>', reply_markup=back_main_admin_kb)
    if message.text == 'Скачать БД':
        await bot.send_document(message.from_user.id, open(r'DB/shop.db', 'rb'), reply_markup=admin_kb)
    if message.text == 'Добавить товар из txt':
        await CustomerStates.admin_txt.set()
        await bot.send_message(message.from_user.id, 'Пришлите .txt файл с товарами в формате:',
                               reply_markup=back_main_admin_kb)
    if message.text == 'Рассылка':
        await CustomerStates.admin_bulk_send.set()
        await bot.send_message(message.from_user.id, 'Напишите сообщение для рассылки',
                               reply_markup=back_main_admin_kb)


# Добавление категории
@dp.message_handler(content_types=types.ContentTypes.TEXT, state=CustomerStates.admin_add_category)
async def admin_add_category(message: types.Message):
    if shop_db.add_category(category_name=message.text):
        await bot.send_message(message.from_user.id, f'Категория <b>{message.text}</b> успешно добавлена',
                               reply_markup=admin_kb)
    else:
        await bot.send_message(message.from_user.id, 'Ошибка добавления', reply_markup=admin_kb)
    await CustomerStates.admin.set()


# Удаление категории
@dp.message_handler(content_types=types.ContentTypes.TEXT, state=CustomerStates.admin_del_category)
async def admin_add_category(message: types.Message):
    if shop_db.del_category(category_name=message.text):
        await bot.send_message(message.from_user.id, f'Категория <b>{message.text}</b> успешно удалена',
                               reply_markup=admin_kb)
    else:
        await bot.send_message(message.from_user.id, 'Ошибка удаления', reply_markup=admin_kb)
    await CustomerStates.admin.set()


# Добавление товара
@dp.message_handler(content_types=types.ContentTypes.TEXT, state=CustomerStates.admin_add_product)
async def admin_add_product(message: types.Message):
    try:
        product = message.text.split(';')
        if len(product) == 4:
            name = product[0]
            cat = product[1]
            price = int(product[2])
            content = product[3]
            if not shop_db.check_category(cat):
                shop_db.add_category(cat)
            if shop_db.add_product([cat, name, price, content]):
                await bot.send_message(message.from_user.id, '<b>Товар успешно добавлен</b>', reply_markup=admin_kb)
        else:
            await bot.send_message(message.from_user.id, 'Ошибка добавления', reply_markup=admin_kb)
    except ValueError:
        bot.send_message(message.from_user.id, 'Ошибка добавления', reply_markup=admin_kb)
    await CustomerStates.admin.set()


# Удаление товара
@dp.message_handler(content_types=types.ContentTypes.TEXT, state=CustomerStates.admin_del_product)
async def admin_del_product(message: types.Message):
    try:
        products = message.text.split(',')
        products = [int(i.strip()) for i in products]
        products = [str(i) for i in products]
        if shop_db.delete_products(product_ids=products):
            await bot.send_message(message.from_user.id, '<b>Товары успешно удалены</b>', reply_markup=admin_kb)
        else:
            await bot.send_message(message.from_user.id, 'Ошибка удаления', reply_markup=admin_kb)
    except ValueError:
        bot.send_message(message.from_user.id, 'Ошибка удаления', reply_markup=admin_kb)
    await CustomerStates.admin.set()


# Выдача купона
@dp.message_handler(content_types=types.ContentTypes.TEXT, state=CustomerStates.admin_coupon)
async def admin_coupon(message: types.Message):
    try:
        coupon = message.text.split(';')
        if len(coupon) == 2:
            user_id = int(coupon[0])
            val = int(coupon[1])
            gen_coupon = shop_db.give_user_coupon(user_id=user_id, coupon_value=val)
            if gen_coupon:
                await bot.send_message(message.from_user.id, f'Купон: {gen_coupon}', reply_markup=admin_kb)
        else:
            await bot.send_message(message.from_user.id, 'Ошибка создания', reply_markup=admin_kb)
    except Exception:
        await bot.send_message(message.from_user.id, 'Ошибка создания', reply_markup=admin_kb)
    await CustomerStates.admin.set()


# Загрузка товаров из .txt
@dp.message_handler(content_types=types.ContentTypes.DOCUMENT, state=CustomerStates.admin_txt)
async def admin_add_product_from_txt(message: types.Message):
    file_info = await bot.get_file(message.document.file_id)
    file = await bot.download_file(file_info.file_path)
    file = file.read().decode()

    log = []
    for num, r in enumerate(file.splitlines()):
        try:
            product = r.split(';')
            if len(product) == 4:
                name = product[0]
                cat = product[1]
                price = int(product[2])
                content = product[3]
                if not shop_db.check_category(cat):
                    shop_db.add_category(cat)
                if shop_db.add_product([cat, name, price, content]):
                    log.append(f'Товар {num + 1} успешно добавлен')
                else:
                    log.append(f'Товар {num + 1} - ошибка добавления')
            else:
                log.append(f'Товар {num + 1} - ошибка добавления')
        except ValueError:
            continue
    await CustomerStates.admin.set()
    await bot.send_message(message.from_user.id, '\n'.join(log), reply_markup=admin_kb)


# Рассылка
@dp.message_handler(content_types=types.ContentTypes.TEXT, state=CustomerStates.admin_bulk_send)
async def admin_bulk_sender(message: types.Message):
    if message.text:
        ids = shop_db.select_users_id()
        print(ids)
        for id in ids:
            try:
                await bot.send_message(id, message.text)
                print(id, message.text)
            except Exception:
                pass
        await bot.send_message(message.from_user.id, 'Разослано', reply_markup=admin_kb)
    else:
        await bot.send_message(message.from_user.id, 'Пустое сообщение', reply_markup=admin_kb)
    await CustomerStates.admin.set()


# ------------------------------------ Баланс ----------------------------------------------------
@dp.message_handler(Text(equals='Баланс💰'), state='*')
async def balance_process(message: types.Message):
    await check_user(message.from_user)
    user = shop_db.check_user(user_id=message.from_user.id)
    if user:
        balance = f'Ваш баланc: <b>{user[2]}</b> руб.'
        await bot.send_message(message.from_user.id, balance, reply_markup=balance_kb)


# Меню пополнить баланс
@dp.message_handler(Text(equals='Пополнить баланс'), state='*')
async def balance_deposit(message: types.Message):
    await bot.send_message(message.from_user.id, 'Выберите способ оплаты', reply_markup=deposit_kb)


# YouMoney спросить на сколько пополнить
@dp.message_handler(Text(equals='Яндекс Деньги 💳'), state='*')
async def yamoney_ask_amount(message: types.Message):
    await CustomerStates.deposit_sum.set()
    await bot.send_message(message.from_user.id, 'Введите сумму, не менее 2 руб.', reply_markup=back_main_kb)


# YouMoney генерация формы платежа
@dp.message_handler(content_types=types.ContentTypes.TEXT, state=CustomerStates.deposit_sum)
async def yamoney_create_url(message: types.Message, state: FSMContext):
    try:
        summ = int(message.text)
    except ValueError:
        await bot.send_message(message.from_user.id, 'Введите целое число', reply_markup=deposit_kb)
        return

    try:
        label, url = payer.create_payment_form(summ)
    except Exception:
        await state.finish()
        await bot.send_message(message.from_user.id, 'Ошибка оплаты', reply_markup=back_main_kb)

    async with state.proxy() as data:
        data['deposit_sum'] = summ
        data['deposit_label'] = label

    await CustomerStates.deposit_wait.set()
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(KeyboardButton('Проверить оплату'))
    kb.add(KeyboardButton('↪️Вернуться в главное меню↩️'))
    msg = f'<a href="{url}"><b>Оплатить</b></a>\nПосле оплаты нажмите кнопку <i>Проверить оплату</i>'
    await bot.send_message(message.from_user.id, msg, reply_markup=kb)


# YouMoney проверка оплаты
@dp.message_handler(Text(equals='Проверить оплату'), state=CustomerStates.deposit_wait)
async def qiwi_deposit(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        summ = data['deposit_sum']
        label = data['deposit_label']

    if payer.check_payment(label) == 'success':
        balance = shop_db.check_user(user_id=message.from_user.id)[2]
        shop_db.update_user(user_id=message.from_user.id, balance=balance + summ)
        msg = f'Баланс пополнен на <b>{summ}</b> руб.\nТекущий баланс <b>{summ + balance}</b> руб.'
        time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        shop_db.update_user(user_id=message.from_user.id, history=['deposit', f"{time} : YouMoney : {summ} руб.\n"])
        await state.finish()
        await bot.send_message(message.from_user.id, msg, reply_markup=main_kb)
    else:
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(KeyboardButton('Проверить оплату'))
        kb.add(KeyboardButton('↪️Вернуться в главное меню↩️'))
        await bot.send_message(message.from_user.id, 'Платеж не найден', reply_markup=kb)


@dp.message_handler(Text(equals='QIWI 🥝'), state='*')
async def qiwi_deposit(message: types.Message):
    await bot.send_message(message.from_user.id, 'QIWI пока не работает', reply_markup=deposit_kb)


# Ввод купона
@dp.message_handler(Text(equals='Активировать купон'), state='*')
async def ask_coupon(message: types.Message):
    await check_user(message.from_user)
    await CustomerStates.coupon_activation.set()
    await bot.send_message(message.from_user.id, 'Введите купон:', reply_markup=back_main_kb)


# Активация купона
@dp.message_handler(content_types=types.ContentTypes.TEXT, state=CustomerStates.coupon_activation)
async def activate_coupon(message: types.Message, state: FSMContext):
    await check_user(message.from_user)
    res = shop_db.use_user_coupon(user_id=message.from_user.id, use_coupon=message.text)
    if res:
        time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        shop_db.update_user(user_id=message.from_user.id, history=['deposit', f"{time} : Купон : {res} руб.\n"])
        await bot.send_message(message.from_user.id, f'Купон номиналом <b>{res}</b> руб. активирован',
                               reply_markup=balance_kb)
    else:
        await bot.send_message(message.from_user.id, 'Такого купона не существует', reply_markup=balance_kb)
    await state.finish()


# ------------------------------------ Личный кабинет ----------------------------------------------------
@dp.message_handler(Text(equals='Личный кабинет👤'), state='*')
async def account_process(message: types.Message):
    await check_user(message.from_user)
    user = shop_db.check_user(user_id=message.from_user.id)
    if user:
        acc_info = f'➖➖➖➖➖➖➖➖➖➖\n' \
                   f'Ваш профиль:\n' \
                   f'🕶️ Ваш ID: <b>{user[0]}</b>\n' \
                   f'👏 Ваш никнейм: <b>@{user[1]}</b>\n' \
                   f'🏦 Ваш текущий баланс: <b>{user[2]}</b> руб.\n' \
                   f'💥 Покупок на сумму: <b>{user[3]}</b> руб.\n' \
                   f'➖➖➖➖➖➖➖➖➖➖'
        await bot.send_message(message.from_user.id, acc_info, reply_markup=account_kb)


@dp.message_handler(Text(equals=['💰Пополнения', '🛒Покупки', '👤Рефералы']), state='*')
async def account_details(message: types.Message):
    await check_user(message.from_user)
    user_history = shop_db.get_user_history(user_id=message.from_user.id)

    if message.text == '💰Пополнения':
        answer = 'Список пополнений:\n'
        if not user_history['deposit']:
            answer = 'Пополнений пока не было'
        else:
            for num, el in enumerate(user_history['deposit']):
                answer += f'{num + 1}. {el}'
    elif message.text == '🛒Покупки':
        answer = 'Список покупок:\n'
        if not user_history['buy']:
            answer = 'Покупок пока не было'
        else:
            for num, el in enumerate(user_history['buy']):
                answer += f'{num + 1}. {el}'
    elif message.text == '👤Рефералы':
        answer = 'Список рефералов:\n'
        if not user_history['referers']:
            answer = 'Нет рефералов'
        else:
            for num, el in enumerate(user_history['referers']):
                answer += f'{num + 1}. {el}'

    await bot.send_message(message.from_user.id, answer, reply_markup=account_kb)


# ------------------------------------ Помощь и инструкции ----------------------------------------------------
@dp.message_handler(Text(equals=['Помощь', 'Инструкции']), state='*')
async def additional_process(message: types.Message):
    await check_user(message.from_user)
    if message.text == 'Помощь':
        answer = 'По всем вопросам обращаться к @Kray68'
    else:
        answer = 'Здесь какие-нибудь инструкции'
    await bot.send_message(message.from_user.id, answer, reply_markup=main_kb)


# ------------------------------------ Наличие товаров ----------------------------------------------------
@dp.message_handler(Text(equals='Наличие товаров'), state='*')
async def shop_list_process(message: types.Message):
    await check_user(message.from_user)
    categories = shop_db.select_categories()
    shop = dict.fromkeys(categories)
    for i in categories:
        shop[i] = shop_db.select_products_by_category(category=i)

    shop_list = ''
    for category, products in shop.items():
        if shop_list:
            shop_list += '\n'
        shop_list += f'➖➖➖ {category} ➖➖➖\n'
        for el in products:
            shop_list += f'{el[0]} | {el[1]} руб/шт | В наличии {el[2]} шт.\n'
    if shop_list:
        await bot.send_message(message.from_user.id, shop_list, reply_markup=main_kb)
    else:
        await bot.send_message(message.from_user.id, 'Нет товаров', reply_markup=main_kb)


# ------------------------------------ Процесс покупки ----------------------------------------------------
# 1. Нажали кнопку купить
@dp.message_handler(Text(equals='Купить💰'), state='*')
async def buy_process(message: types.Message):
    await check_user(message.from_user)
    # Make keyboard from Categories
    categories = shop_db.select_categories()
    buy_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    buy_kb.add(KeyboardButton('↪️Вернуться в главное меню↩️'))
    [buy_kb.add(KeyboardButton(i)) for i in categories]
    await CustomerStates.categories.set()
    await message.reply("Выберите <b>категорию</b>", reply_markup=buy_kb)


# 2. Выбрали категорию
@dp.message_handler(content_types=types.ContentTypes.TEXT, state=CustomerStates.categories)
async def category_choose(message: types.Message, state: FSMContext):
    await check_user(message.from_user)
    if message.text in shop_db.select_categories():
        products = shop_db.select_products_by_category(message.text)
        product_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
        product_kb.row(KeyboardButton('🔙Назад'), KeyboardButton('↪️Вернуться в главное меню↩️'))
        [product_kb.add(KeyboardButton(f'{i[0]} | Цена: {i[1]} руб. | В наличии: {i[2]} шт.')) for i in products]
        async with state.proxy() as data:
            data['category'] = message.text
        await CustomerStates.buy_choose.set()
        await bot.send_message(message.from_user.id, f"Вы выбрали категорию {message.text}", reply_markup=product_kb)


@dp.message_handler(Text(equals='🔙Назад'), state=CustomerStates.buy_choose)
async def back_to_categories(message: types.Message):
    await check_user(message.from_user)
    await buy_process(message)


# 3. Выбрали товар
@dp.message_handler(regexp=r'(.+) \| Цена: (\d+) руб\. \| В наличии: (\d+) шт\.', state=CustomerStates.buy_choose)
async def enter_product(message: types.Message, state: FSMContext):
    await check_user(message.from_user)
    product = re.match(re.compile(r'(.+) \| Цена: (\d+) руб\. \| В наличии: (\d+) шт\.'), message.text)
    name = product.group(1)
    price = product.group(2)
    quantity = product.group(3)

    async with state.proxy() as data:
        data['name'] = name
        data['price'] = int(price)
        data['quantity'] = int(quantity)
        data['purchase_id'] = shop_db.generate_coupon(10)

    answer = f'Наименование товара: <b>{name}</b>\n' \
             f'Цена: <b>{price}</b> руб.\n' \
             f'В наличии: <b>{quantity}</b> шт.\n' \
             f'Введите требуемое количество товаров:'

    await CustomerStates.buy_count.set()
    await bot.send_message(message.from_user.id, answer, reply_markup=back_main_kb)


# 4. Ввели количество товара
@dp.message_handler(content_types=types.ContentTypes.TEXT, state=CustomerStates.buy_count)
async def product_count(message: types.Message, state: FSMContext):
    await check_user(message.from_user)
    async with state.proxy() as data:
        category = data['category']
        name = data['name']
        price = data['price']
        quantity = data['quantity']
        purchase_id = data['purchase_id']

    try:
        buy_count = int(message.text)
        if buy_count <= 0 or buy_count > quantity:
            await bot.send_message(message.from_user.id, f"Неправильное количество", reply_markup=back_main_kb)
            return
    except ValueError:
        await bot.send_message(message.from_user.id, f"Введите целое число", reply_markup=back_main_kb)
        return

    # Проверить еще раз количество и если все норм то забронировать товар
    # (удалить из бд, добавить в данные пользователя) на какое то время / до момента покупки
    product = shop_db.get_product(category=category, name=name, price=price, quantity=buy_count)
    if product and len(product) == buy_count:
        shop_db.delete_products(product_ids=[str(i[0]) for i in product])

        buy_check = buy_count * price
        answer = f'Покупка товара: <b>{name}</b>\n' \
                 f'(У Вас <b>2 минуты</b>, чтобы подтвердить оплату)\n' \
                 f'Количество товара: <b>{buy_count}</b> шт.\n' \
                 f'К оплате: <b>{buy_check}</b> руб.\n' \
                 f'Подтвердите покупку товара, нажав кнопку ниже'

        async with state.proxy() as data:
            data['buy_count'] = buy_count
            data['buy_check'] = buy_check
            data['products'] = product

        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(KeyboardButton('Подтвердить'))
        kb.add(KeyboardButton('↪️Вернуться в главное меню↩️'))
        await CustomerStates.buy_confirm.set()
        await bot.send_message(message.from_user.id, answer, reply_markup=kb)

        # Проверка, ушел ли он отсюда, если нет и прошло время резерва, то вернуть товар в бд
        await asyncio.sleep(120)
        current_state = await state.get_state()
        if current_state is not None and current_state == 'CustomerStates:buy_confirm':
            async with state.proxy() as data:
                if data['purchase_id'] == purchase_id:
                    await state.finish()
                    await bot.send_message(message.from_user.id, 'Время резерва истекло', reply_markup=main_kb)
                    [shop_db.add_product(product=[category, name, price, p[1]]) for p in product]
    else:
        await state.finish()
        msg = 'Ошибка получения товара.\nВероятно требуемое количество уже недоступно, попробуйте еще раз'
        await bot.send_message(message.from_user.id, msg, reply_markup=main_kb)


# 5. Подтвердили покупку
@dp.message_handler(Text(equals='Подтвердить'), state=CustomerStates.buy_confirm)
async def product_count(message: types.Message, state: FSMContext):
    await check_user(message.from_user)
    async with state.proxy() as data:
        name = data['name']
        category = data['category']
        price = data['price']
        buy_count = data['buy_count']
        buy_check = data['buy_check']
        product = data['products']

    user_id, user_name, user_balance, user_spent = shop_db.check_user(user_id=message.from_user.id)

    # Если все норм то выдать забронированный товар покупателю, если не норм то вернуть его в бд
    if user_balance >= buy_check:
        time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        contents = '\n'.join([i[1] for i in product])
        answer = f'Наименование: <b>{name}</b>\n' \
                 f'Время покупки: <b>{time}</b>\n' \
                 f'Цена: <b>{price}</b> руб/шт\n' \
                 f'Количество: <b>{buy_count}</b> шт.\n' \
                 f'Остаток на счете: <b>{user_balance - buy_check}</b> руб.\n\n' \
                 f'<b>Товар</b>:\n\n{contents}'
        res = await bot.send_message(message.from_user.id, answer, reply_markup=back_main_kb)
        await state.finish()
        if res:
            history = ['buy', f"{time} : {category} : {name} : {buy_count} шт. : {buy_check} руб.\n"]
            shop_db.update_user(balance=user_balance - buy_check, spent=user_spent + buy_check, history=history,
                                user_id=user_id)
        else:
            # Вернуть товар в бд
            [shop_db.add_product(product=[category, name, price, p[1]]) for p in product]
            await bot.send_message(message.from_user.id, 'Ошибка', reply_markup=back_main_kb)
    else:
        # Вернуть товар в бд
        [shop_db.add_product(product=[category, name, price, p[1]]) for p in product]
        await state.finish()
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(KeyboardButton('Пополнить баланс'))
        kb.add(KeyboardButton('↪️Вернуться в главное меню↩️'))
        msg = f'Недостаточно средств.\nВаш баланс: <b>{user_balance} руб.</b>\n' \
              f'Не хватает: <b>{buy_check - user_balance} руб.</b>'
        await bot.send_message(message.from_user.id, msg, reply_markup=kb)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
