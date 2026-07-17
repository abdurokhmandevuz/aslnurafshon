import re
import os

translations = {
    'Buyurtmalar tarixi': 'История заказов',
    'Barcha joriy va oldingi buyurtmalaringiz.': 'Все ваши текущие и предыдущие заказы.',
    'Barchasi': 'Все',
    'Faol': 'Активные',
    'Tugallangan': 'Завершенные',
    'Buyurtma': 'Заказ',
    'Umumiy summa:': 'Общая сумма:',
    'Buyurtmalar topilmadi.': 'Заказы не найдены.',
    'Manzilni tanlang': 'Выберите адрес',
    'Manzil qidirilmoqda...': 'Поиск адреса...',
    'Tasdiqlash': 'Подтвердить',
    "Manzilni aniqlab bo'lmadi.": 'Не удалось определить адрес.',
    'Xatolik yuz berdi.': 'Произошла ошибка.',
    'Buyurtmani rasmiylashtirish': 'Оформить заказ',
    "Yetkazib berish ma'lumotlarini kiriting.": 'Введите информацию о доставке.',
    'Yetkazib berish': 'Доставка',
    "Do'kondan olib ketish": 'Самовывоз',
    'Aloqa uchun telefon raqam': 'Номер телефона для связи',
    'Iltimos, telefon raqamingizni kiriting.': 'Пожалуйста, введите свой номер телефона.',
    'Yetkazib berish manzili': 'Адрес доставки',
    'Manzilni kiriting yoki xaritadan tanlang': 'Введите адрес или выберите на карте',
    'Xaritadan tanlash': 'Выбрать на карте',
    'Yetkazib berish vaqti': 'Время доставки',
    'Bugun': 'Сегодня',
    'Tez orada': 'Скоро',
    'Ertaga': 'Завтра',
    "To'lov usuli": 'Способ оплаты',
    'Naqd': 'Наличные',
    'Buyurtma tarkibi': 'Состав заказа',
    'Mahsulotlar summasi': 'Сумма продуктов',
    "Jami to'lov": 'Итого к оплате',
    'Mahsulotlar topilmadi.': 'Товары не найдены.',
    'Variantlar': 'Варианты',
    'Tugagan': 'Закончился',
    'Variantlar mavjud emas': 'Варианты недоступны',
    'Mahsulot haqida': 'О товаре',
    "Savatga qo'shish": 'Добавить в корзину',
    'Iltimos, variantni tanlang.': 'Пожалуйста, выберите вариант.',
    'Yuklanmoqda...': 'Загрузка...',
    'Kuting...': 'Подождите...',
    'ta buyurtma': 'заказ(ов)',
    'Saqlangan manzillar': 'Сохраненные адреса',
    'Uy, Ishxona': 'Дом, Работа',
    'Sozlamalar': 'Настройки',
    "Yordam va qo'llab-quvvatlash": 'Помощь и поддержка',
    'Ilova haqida': 'О приложении',
    'Tizimdan chiqish': 'Выйти из системы',
    'Foydalanuvchi': 'Пользователь',
    'Telefon raqam kiritilmagan': 'Номер телефона не указан',
    'Foydalanuvchi topilmadi': 'Пользователь не найден',
    'Iltimos, bot orqali qayta kiring': 'Пожалуйста, войдите снова через бот',
    'Sizning savatingiz': 'Ваша корзина',
    "O'chirish": 'Удалить',
    'Promo-kodni kiriting': 'Введите промокод',
    "Qo'llash": 'Применить',
    "Savatingiz bo'sh": 'Ваша корзина пуста',
    'Xaridni boshlash uchun mahsulotlarni katalogdan tanlang.': 'Выберите товары в каталоге, чтобы начать покупки.',
    "Katalogga o'tish": 'Перейти в каталог',
    'Buyurtma xulosasi': 'Сводка заказа',
    'Mahsulotlar': 'Товары',
    'Chegirma': 'Скидка',
    'Jami': 'Итого',
    "Xavfsiz to'lov va tezkor yetkazib berish kafolatlangan.": 'Безопасная оплата и быстрая доставка гарантированы.',
    'Qayta buyurtma': 'Повторить заказ',
    'Sevimlilar': 'Избранное',
    "Sevimli mahsulotlar yo'q.": 'Нет избранных товаров.',
    'Kuryer paneli': 'Панель курьера',
    'Mening buyurtmalarim': 'Мои заказы',
    'Yangi buyurtmalar (Kutish zalida)': 'Новые заказы (Зал ожидания)',
    'Sizda faol buyurtmalar yo\'q.': 'У вас нет активных заказов.',
    'Hozircha yangi buyurtmalar yo\'q.': 'Новых заказов пока нет.',
    'Yo\'lga chiqish': 'Выехать в путь',
    'Qabul qilish': 'Принять',
    'Minimal buyurtma summasi': 'Минимальная сумма заказа',
    'Iltimos, savatga yana mahsulot qo\'shing.': 'Пожалуйста, добавьте еще товаров в корзину.'
}

po_path = 'locale/ru/LC_MESSAGES/django.po'
with open(po_path, 'r', encoding='utf-8') as f:
    content = f.read()

# We need to find entries of the form:
# [#, fuzzy\n][#| msgid "..."\n]msgid "..."\nmsgstr "..."
# and translate them.

# First split the file by empty lines to get individual message blocks
blocks = content.split('\n\n')
updated_blocks = []

for block in blocks:
    lines = block.split('\n')
    msgid = None
    msgid_idx = -1
    msgstr_idx = -1
    fuzzy_idx = -1
    previous_msgid_idx = -1
    
    for i, line in enumerate(lines):
        if line.startswith('msgid '):
            msgid = re.match(r'msgid "(.*)"', line).group(1)
            msgid_idx = i
        elif line.startswith('msgstr '):
            msgstr_idx = i
        elif line.strip() == '#, fuzzy':
            fuzzy_idx = i
        elif line.startswith('#| msgid '):
            previous_msgid_idx = i

    if msgid in translations:
        # Update msgstr
        lines[msgstr_idx] = f'msgstr "{translations[msgid]}"'
        # Remove fuzzy markers
        if fuzzy_idx != -1:
            lines[fuzzy_idx] = ''
        if previous_msgid_idx != -1:
            lines[previous_msgid_idx] = ''
        
        # Filter out empty lines we just created
        lines = [l for l in lines if l != '']
        
    updated_blocks.append('\n'.join(lines))

new_content = '\n\n'.join(updated_blocks)

with open(po_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Translation processed successfully!")
