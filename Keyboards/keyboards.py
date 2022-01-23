from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, \
                          InlineKeyboardButton


main_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
main_kb.row(KeyboardButton('Купить💰'), KeyboardButton('Наличие товаров'))
main_kb.row(KeyboardButton('Личный кабинет👤'), KeyboardButton('Баланс💰'))
main_kb.row(KeyboardButton('Помощь'), KeyboardButton('Инструкции'))


account_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
account_kb.row(KeyboardButton('💰Пополнения'), KeyboardButton('🛒Покупки'), KeyboardButton('👤Рефералы'))
account_kb.add(KeyboardButton('↪️Вернуться в главное меню↩️'))


balance_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
balance_kb.row(KeyboardButton('Пополнить баланс'), KeyboardButton('Активировать купон'))
balance_kb.add(KeyboardButton('↪️Вернуться в главное меню↩️'))


deposit_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
deposit_kb.row(KeyboardButton('Яндекс Деньги 💳'), KeyboardButton('QIWI 🥝'))
deposit_kb.add(KeyboardButton('↪️Вернуться в главное меню↩️'))


back_main_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
back_main_kb.add(KeyboardButton('↪️Вернуться в главное меню↩️'))


admin_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
admin_kb.row(KeyboardButton('Добавить категорию'), KeyboardButton('Удалить категорию'))
admin_kb.row(KeyboardButton('Добавить товар'), KeyboardButton('Удалить товар'))
admin_kb.row(KeyboardButton('Создать купон'), KeyboardButton('Скачать БД'))
admin_kb.row(KeyboardButton('Добавить товар из txt'), KeyboardButton('Рассылка'))
admin_kb.add(KeyboardButton('↪️Вернуться в главное меню↩️'))


back_main_admin_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
back_main_admin_kb.add(KeyboardButton('К админке'))
back_main_admin_kb.add(KeyboardButton('↪️Вернуться в главное меню↩️'))