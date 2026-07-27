"""
Telegram bot handlers — Mukammal va tezkor versiya.

Imkoniyatlar:
  - /start va Reply Keyboard (Do'kon WebApp, Botda buyurtma, Qayta buyurtma, Aloqa)
  - Bot ichida choy va kofelarni ko'rish hamda savatga yig'ish
  - Telefon raqamni 1 bosishda (request_contact) va Lokatsiyani 1 bosishda (request_location) yuborish
  - DB dan faol Bank kartasini ko'rsatish
  - Chek fotosuratini yuklash (photo handler) → Order.payment_proof va Adminga foto bilan yuborish
  - 🔄 Oxirgi buyurtmani 1-bosishda takrorlash (Fast Re-order)
  - Admin guruhida [✅ To'lovni tasdiqlash], [🚚 Yo'lga chiqdi], [❌ Rad etish]
"""
import logging
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

import django
django.setup()

from django.conf import settings
from aiogram import F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.keyboards import (
    main_menu_keyboard,
    main_reply_keyboard,
    shop_keyboard,
    orders_keyboard,
    promo_keyboard,
    categories_inline_keyboard,
    products_inline_keyboard,
    product_detail_inline_keyboard,
    cart_inline_keyboard,
    request_phone_keyboard,
    request_location_keyboard,
    order_admin_keyboard,
    order_delivered_keyboard,
    saved_addresses_keyboard,
    profile_inline_keyboard,
    settings_inline_keyboard,
)

logger = logging.getLogger(__name__)
router = Router()


async def safe_edit_message(message: Message, text: str, reply_markup=None, parse_mode='HTML'):
    """Safe message updater that works on both text messages and photo messages cleanly."""
    try:
        if message.photo:
            try:
                await message.delete()
            except Exception:
                pass
            return await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            return await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        return await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)


# ─── FSM States for Bot Ordering Flow ─────────────────────────────────────────

class OrderState(StatesGroup):
    waiting_for_promocode = State()
    waiting_for_phone = State()
    waiting_for_location = State()
    waiting_for_receipt = State()


class UserSettingsState(StatesGroup):
    waiting_for_new_phone = State()
    waiting_for_new_address = State()


# In-memory user cart storage: { user_id: { variant_id: quantity } }
USER_CARTS = {}
USER_CARTS_DEAL_FLAGS = {}
# Pending order for receipt upload: { user_id: order_id }
PENDING_RECEIPT_ORDERS = {}


STATUS_EMOJI  = {'yangi':'🆕','tayyorlanmoqda':'👨‍🍳','yolda':'🚚','yetkazildi':'✅','bekor_qilindi':'❌'}
STATUS_LABEL  = {'yangi':'Yangi','tayyorlanmoqda':'Tayyorlanmoqda','yolda':"Yo'lda",'yetkazildi':'Yetkazildi','bekor_qilindi':'Bekor qilindi'}
STATUS_MAP    = {'confirm':'tayyorlanmoqda','dispatch':'yolda','delivered':'yetkazildi','cancel':'bekor_qilindi'}

CONTACT_TEXT = (
    "📞 <b>Asl Nurafshon — Aloqa</b>\n\n"
    "📱 Telefon: <b>+998 90 000 00 00</b>\n"
    "📍 Manzil: <b>Nurafshon sh., Navoiy ko'chasi 12</b>\n"
    "⏰ Ish vaqti: <b>09:00 — 22:00</b>\n\n"
    "Savollaringiz bo'lsa shu chatga yozing, operatorlarimiz yordam beradi."
)


# ─── /start ───────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user

    try:
        from asgiref.sync import sync_to_async
        from apps.accounts.models import TelegramUser
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        await sync_to_async(TelegramUser.objects.update_or_create)(
            telegram_id=user.id,
            defaults={'full_name': full_name or str(user.id), 'username': user.username or ''},
        )
    except Exception as e:
        logger.warning("save_user error: %s", e)

    welcome_text = (
        f"Assalomu alaykum, <b>{user.first_name}</b>! 👋\n\n"
        "☕ <b>Asl Nurafshon</b> — premium choy va kofe do'koniga xush kelibsiz!\n\n"
        "Bizning do'konimizda eng yuqori sifatli va xushbo'y choy hamda kofe mahsulotlarini qulay tarzda buyurtma qilishingiz mumkin.\n\n"
        "Quyidagi menyudan kerakli bo'limni tanlang 👇"
    )

    await message.answer(
        welcome_text,
        parse_mode='HTML',
        reply_markup=main_reply_keyboard(),
    )
    await message.answer(
        "<b>Do'kon Bosh Menusi:</b>",
        parse_mode='HTML',
        reply_markup=main_menu_keyboard(settings.FRONTEND_URL),
    )


@router.message(F.text == "🛍 Do'konni ochish (Web)")
async def handle_open_web_shop(message: Message, state: FSMContext):
    await state.clear()
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
    from bot.keyboards import _url
    markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🌐 Web App Do'konni Ochish",
            web_app=WebAppInfo(url=_url(settings.FRONTEND_URL, "index.html")),
            style="primary",
        )
    ]])
    await message.answer(
        "🌐 <b>Asl Nurafshon Web App do'koni</b>\n\n"
        "Quyidagi tugmani bosib, interaktiv veb-do'konimizni ochishingiz va mahsulotlarni qulay tarzda ko'rishingiz mumkin 👇",
        parse_mode='HTML',
        reply_markup=markup,
    )


@router.message(F.text.in_({"☕ Choy tanlash (Bot)", "☕ Bot Katalogi", "/catalog"}))
@router.callback_query(F.data == "bot_catalog")
async def show_bot_catalog(event: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    from asgiref.sync import sync_to_async
    from apps.catalog.models import Category

    categories = await sync_to_async(lambda: list(Category.objects.filter(is_active=True)))()

    text = "🍵 <b>Barcha kategoriyalar:</b>\n\nQuyidagi bo'limlardan birini tanlang 👇"
    markup = categories_inline_keyboard(categories)

    if isinstance(event, CallbackQuery):
        await safe_edit_message(event.message, text, reply_markup=markup)
        await event.answer()
    else:
        await event.answer(text, parse_mode='HTML', reply_markup=markup)


@router.callback_query(F.data.startswith("cat:"))
async def show_category_products(callback: CallbackQuery):
    cat_id = int(callback.data.split(":")[1])
    from asgiref.sync import sync_to_async
    from apps.catalog.models import Product, Category

    cat = await sync_to_async(Category.objects.get)(id=cat_id)
    products = await sync_to_async(lambda: list(Product.objects.filter(category_id=cat_id, is_active=True)))()

    if not products:
        await callback.answer("Ushbu kategoriyada mahsulotlar yo'q.", show_alert=True)
        return

    text = f"🍵 <b>{cat.name}</b> bo'limi mahsulotlari:\n\nBatafsil ko'rish uchun bosing 👇"
    markup = products_inline_keyboard(products, cat_id)
    await safe_edit_message(callback.message, text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data.startswith("prod:"))
async def show_product_detail(callback: CallbackQuery):
    prod_id = int(callback.data.split(":")[1])
    from asgiref.sync import sync_to_async
    from apps.catalog.models import Product, ProductVariant

    product = await sync_to_async(Product.objects.prefetch_related('variants').get)(id=prod_id)
    variants = [v for v in product.variants.all() if v.is_available]

    if not variants:
        await callback.answer("Hozirda bu mahsulot mavjud emas", show_alert=True)
        return

    desc = product.description or "Ajoyib ta'm va yuqori sifatli choy."
    text = (
        f"🍃 <b>{product.name}</b>\n\n"
        f"<i>{desc}</i>\n\n"
        f"<b>Mavjud variantlar (og'irligi):</b>\n"
    )
    for v in variants:
        label = v.label or f"{v.weight_grams}g"
        text += f"• {label}: <b>{v.price:,} UZS</b>\n"

    markup = product_detail_inline_keyboard(prod_id, variants)

    if product.image:
        try:
            from aiogram.types import FSInputFile
            await callback.message.answer_photo(
                photo=FSInputFile(product.image.path) if hasattr(product.image, 'path') else product.image.url,
                caption=text,
                parse_mode='HTML',
                reply_markup=markup
            )
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.answer()
            return
        except Exception:
            pass

    await safe_edit_message(callback.message, text, reply_markup=markup)
    await callback.answer()


# ─── User Profile & Settings ──────────────────────────────────────────────────

@router.message(F.text.in_({"👤 Profil", "/profile"}))
@router.callback_query(F.data == "user_profile")
async def show_user_profile(event: Message | CallbackQuery):
    user_id = event.from_user.id
    from asgiref.sync import sync_to_async
    from apps.accounts.models import TelegramUser
    from apps.orders.models import Order

    @sync_to_async
    def get_profile_data():
        tuser = TelegramUser.objects.filter(telegram_id=user_id).first()
        if not tuser:
            return None
        orders_count = Order.objects.filter(user=tuser).count()
        addresses_count = tuser.addresses.count()
        return tuser, orders_count, addresses_count

    data = await get_profile_data()
    if not data or not data[0]:
        text = "👤 <b>Mening Profilim</b>\n\nMa'lumotlar hali yaratilmagan."
    else:
        tuser, orders_count, addresses_count = data
        phone_str = tuser.phone or "Kiritilmagan"
        text = (
            f"👤 <b>Mening Profilim</b>\n\n"
            f"👤 Ism: <b>{tuser.full_name}</b>\n"
            f"📱 Telefon: <b>{phone_str}</b>\n"
            f"📦 Buyurtmalar soni: <b>{orders_count} ta</b>\n"
            f"📍 Saqlangan manzillar: <b>{addresses_count} ta</b>\n"
            f"💰 Keshbek balansi: <b>{tuser.cashback_balance:,} UZS</b>"
        )

    if isinstance(event, CallbackQuery):
        await safe_edit_message(event.message, text, reply_markup=profile_inline_keyboard())
        await event.answer()
    else:
        await event.answer(text, parse_mode='HTML', reply_markup=profile_inline_keyboard())


@router.message(F.text.in_({"⚙️ Sozlamalar", "/settings"}))
@router.callback_query(F.data == "user_settings")
async def show_user_settings(event: Message | CallbackQuery):
    text = (
        "⚙️ <b>Sozlamalar paneli</b>\n\n"
        "Quyidagi tugmalar orqali profil ma'lumotlaringizni tahrirlashingiz mumkin 👇"
    )
    if isinstance(event, CallbackQuery):
        await safe_edit_message(event.message, text, reply_markup=settings_inline_keyboard())
        await event.answer()
    else:
        await event.answer(text, parse_mode='HTML', reply_markup=settings_inline_keyboard())


# ─── Settings Action Handlers ──────────────────────────────────────────────────

@router.callback_query(F.data == "change_phone")
async def handle_change_phone(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserSettingsState.waiting_for_new_phone)
    await callback.message.answer(
        "📱 <b>Yangi telefon raqamingizni yuboring:</b>\n\nTugmani bosing yoki raqamni yozing 👇",
        parse_mode='HTML',
        reply_markup=request_phone_keyboard()
    )
    await callback.answer()


@router.message(UserSettingsState.waiting_for_new_phone)
async def process_new_phone(message: Message, state: FSMContext):
    phone = ""
    if message.contact:
        phone = message.contact.phone_number
    elif message.text and message.text != "❌ Bekor qilish":
        phone = message.text.strip()
    else:
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_reply_keyboard())
        return

    user_id = message.from_user.id
    from asgiref.sync import sync_to_async
    from apps.accounts.models import TelegramUser

    @sync_to_async
    def update_user_phone():
        tuser, _ = TelegramUser.objects.get_or_create(
            telegram_id=user_id,
            defaults={'full_name': message.from_user.full_name}
        )
        tuser.phone = phone
        tuser.save(update_fields=['phone'])
        return tuser

    await update_user_phone()
    await state.clear()
    await message.answer(
        f"✅ Telefon raqamingiz muvaffaqiyatli yangilandi: <b>{phone}</b>",
        parse_mode='HTML',
        reply_markup=main_reply_keyboard()
    )


@router.callback_query(F.data == "manage_addresses")
async def handle_manage_addresses(callback: CallbackQuery):
    user_id = callback.from_user.id
    from asgiref.sync import sync_to_async
    from apps.accounts.models import Address

    addresses = await sync_to_async(lambda: list(Address.objects.filter(user__telegram_id=user_id)))()

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    if not addresses:
        text = "📍 <b>Sizda hali saqlangan manzillar yo'q.</b>\n\nYangi manzil qo'shish uchun tugmani bosing 👇"
        buttons = [
            [InlineKeyboardButton(text="➕ Yangi manzil qo'shish", callback_data="add_address")],
            [InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="user_settings")],
        ]
    else:
        text = "📍 <b>Saqlangan manzillaringiz:</b>\n"
        buttons = []
        for idx, addr in enumerate(addresses, 1):
            text += f"\n<b>{idx}.</b> {addr.address_text}"
            buttons.append([
                InlineKeyboardButton(text=f"🗑 {idx}-manzilni o'chirish", callback_data=f"del_addr:{addr.id}")
            ])
        buttons.append([InlineKeyboardButton(text="➕ Yangi manzil qo'shish", callback_data="add_address")])
        buttons.append([InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="user_settings")])

    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await safe_edit_message(callback.message, text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data == "add_address")
async def handle_add_address(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserSettingsState.waiting_for_new_address)
    await callback.message.answer(
        "📍 <b>Yangi manzilni yuboring:</b>\n\nJoylashuv tugmasini bosing yoki matn shaklida yozing 👇",
        parse_mode='HTML',
        reply_markup=request_location_keyboard()
    )
    await callback.answer()


@router.message(UserSettingsState.waiting_for_new_address)
async def process_new_address(message: Message, state: FSMContext):
    if message.text in {"✏️ Manzilni matn qilib yozish", "Manzilni matn qilib yozish"}:
        await message.answer(
            "✍️ <b>Manzilingizni matn ko'rinishida yozib yuboring:</b>\n"
            "<i>(Masalan: Nurafshon sh., Navoiy ko'chasi 12-uy)</i>",
            parse_mode='HTML'
        )
        return

    address_text = ""
    if message.location:
        address_text = f"GPS: {message.location.latitude}, {message.location.longitude}"
    elif message.text and message.text != "❌ Bekor qilish":
        address_text = message.text.strip()
    else:
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_reply_keyboard())
        return

    user_id = message.from_user.id
    from asgiref.sync import sync_to_async
    from apps.accounts.models import TelegramUser, Address

    @sync_to_async
    def save_address():
        tuser, _ = TelegramUser.objects.get_or_create(
            telegram_id=user_id,
            defaults={'full_name': message.from_user.full_name}
        )
        return Address.objects.create(user=tuser, address_text=address_text, title="Manzil")

    await save_address()
    await state.clear()
    await message.answer(
        f"✅ Yangi manzil saqlandi:\n<b>{address_text}</b>",
        parse_mode='HTML',
        reply_markup=main_reply_keyboard()
    )


@router.callback_query(F.data.startswith("del_addr:"))
async def handle_delete_address(callback: CallbackQuery):
    addr_id = int(callback.data.split(":")[1])
    from asgiref.sync import sync_to_async
    from apps.accounts.models import Address

    @sync_to_async
    def delete_addr():
        Address.objects.filter(id=addr_id, user__telegram_id=callback.from_user.id).delete()

    await delete_addr()
    await callback.answer("🗑 Manzil o'chirildi", show_alert=True)
    await handle_manage_addresses(callback)


# ─── Add Variant to Cart ──────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("addvar:"))
async def add_variant_to_cart(callback: CallbackQuery):
    var_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id

    if user_id not in USER_CARTS:
        USER_CARTS[user_id] = {}

    USER_CARTS[user_id][var_id] = USER_CARTS[user_id].get(var_id, 0) + 1

    from asgiref.sync import sync_to_async
    from apps.catalog.models import ProductVariant
    variant = await sync_to_async(ProductVariant.objects.select_related('product').get)(id=var_id)

    total_count = sum(USER_CARTS[user_id].values())
    await callback.answer(f"✅ {variant.product.name} ({variant.label}) savatga qo'shildi! (Jami: {total_count} ta)", show_alert=True)


# ─── Add Daily Deal to Cart ───────────────────────────────────────────────────

@router.callback_query(F.data.startswith("add_deal:"))
async def handle_add_deal_to_cart(callback: CallbackQuery):
    deal_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id

    from asgiref.sync import sync_to_async
    from apps.catalog.models import DailyDeal
    from django.utils import timezone

    try:
        deal = await sync_to_async(DailyDeal.objects.select_related('variant', 'variant__product').get)(id=deal_id)
        if not deal.is_active or (deal.ends_at and timezone.now() > deal.ends_at):
            await callback.answer("⚠️ Ushbu kunlik taklif muddati tugagan!", show_alert=True)
            return

        var_id = deal.variant.id
        if user_id not in USER_CARTS:
            USER_CARTS[user_id] = {}

        USER_CARTS[user_id][var_id] = USER_CARTS[user_id].get(var_id, 0) + 1
        USER_CARTS_DEAL_FLAGS[user_id] = True

        total_count = sum(USER_CARTS[user_id].values())
        await callback.answer(
            f"🔥 {deal.variant.product.name} (Kunlik taklif -{deal.discount_percent}%) savatga qo'shildi! (Jami: {total_count} ta)",
            show_alert=True
        )
    except Exception as err:
        logger.error("Add deal error: %s", err)
        await callback.answer("Taklif topilmadi", show_alert=True)


# ─── Apply Promocode Flow ─────────────────────────────────────────────────────

@router.callback_query(F.data == "apply_promocode")
async def handle_apply_promocode(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if USER_CARTS_DEAL_FLAGS.get(user_id, False):
        await callback.message.answer(
            "⚠️ <b>Kechirasiz, promo-kod qo'llab bo'lmaydi!</b>\n\n"
            "Savatingizda <b>Kunlik taklif (Daily Deal)</b> yoki chegirmali mahsulot borligi sababli promo-kod ishlatish mumkin emas.",
            parse_mode='HTML'
        )
        await callback.answer()
        return

    await state.set_state(OrderState.waiting_for_promocode)
    await callback.message.answer(
        "🎁 <b>Promo-kodni kiriting:</b>\n\n<i>(Masalan: NURAFSHON10)</i>",
        parse_mode='HTML'
    )
    await callback.answer()


@router.message(OrderState.waiting_for_promocode)
async def process_promocode(message: Message, state: FSMContext):
    code_text = (message.text or '').strip().upper()
    user_id = message.from_user.id

    from asgiref.sync import sync_to_async
    from apps.orders.models import PromoCode
    from apps.accounts.models import TelegramUser

    @sync_to_async
    def check_promo():
        promo = PromoCode.objects.filter(code=code_text, is_active=True).first()
        if not promo:
            return None, "⚠️ Promo-kod topilmadi yoki aktiv emas."
        if not promo.is_valid():
            return None, "⚠️ Promo-kod muddati o'tgan yoki ishlatish limiti tugagan."

        tuser = TelegramUser.objects.filter(telegram_id=user_id).first()
        if tuser and promo.used_by_users.filter(id=tuser.id).exists():
            return None, "⚠️ Siz ushbu promo-koddan avval foydalangansiz! Har bir promo-kod 1 kishiga faqat 1 marta beriladi."

        return promo, None

    promo, err_msg = await check_promo()
    if err_msg:
        await message.answer(err_msg, parse_mode='HTML')
        await state.clear()
        return

    await state.update_data(applied_promo_code=promo.code, promo_discount_percent=promo.discount_percent)
    await state.clear()
    await message.answer(
        f"✅ <b>PROMO-KOD QO'LLANDI!</b>\n\nPromo-kod: <b>{promo.code}</b> (-{promo.discount_percent}% chegirma)",
        parse_mode='HTML',
        reply_markup=main_reply_keyboard()
    )


# ─── View Cart & Quantity Controls ───────────────────────────────────────────

@router.callback_query(F.data.startswith("cart_inc:"))
async def handle_cart_inc(callback: CallbackQuery):
    var_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    if user_id in USER_CARTS and var_id in USER_CARTS[user_id]:
        USER_CARTS[user_id][var_id] += 1
    await view_bot_cart(callback)


@router.callback_query(F.data.startswith("cart_dec:"))
async def handle_cart_dec(callback: CallbackQuery):
    var_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    if user_id in USER_CARTS and var_id in USER_CARTS[user_id]:
        USER_CARTS[user_id][var_id] -= 1
        if USER_CARTS[user_id][var_id] <= 0:
            USER_CARTS[user_id].pop(var_id)
    await view_bot_cart(callback)


@router.callback_query(F.data.startswith("cart_del:"))
async def handle_cart_del(callback: CallbackQuery):
    var_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    if user_id in USER_CARTS and var_id in USER_CARTS[user_id]:
        USER_CARTS[user_id].pop(var_id)
    await view_bot_cart(callback)


@router.callback_query(F.data == "view_cart")
async def view_bot_cart(callback: CallbackQuery):
    user_id = callback.from_user.id
    cart = USER_CARTS.get(user_id, {})

    if not cart:
        await safe_edit_message(
            callback.message,
            "🛒 <b>Savatingiz bo'sh.</b>\n\nKatalogdan mahsulotlarni tanlang!",
            reply_markup=cart_inline_keyboard(cart=None)
        )
        await callback.answer()
        return

    from asgiref.sync import sync_to_async
    from apps.catalog.models import ProductVariant

    variant_ids = list(cart.keys())
    variants = await sync_to_async(lambda: list(ProductVariant.objects.filter(id__in=variant_ids).select_related('product')))()
    variants_dict = {v.id: v for v in variants}

    total_sum = 0
    lines = ["🛒 <b>Savatdagi mahsulotlar:</b>\n"]

    for v in variants:
        qty = cart.get(v.id, 0)
        if qty <= 0:
            continue
        item_total = v.price * qty
        total_sum += item_total
        lines.append(f"• <b>{v.product.name}</b> ({v.label})\n  {qty} ta × {v.price:,} = <b>{item_total:,} UZS</b>")

    delivery_fee = 0 if total_sum >= 150000 else 15000
    grand_total = total_sum + delivery_fee

    lines.append(f"\nMahsulotlar: <b>{total_sum:,} UZS</b>")
    lines.append(f"Yetkazib berish: <b>{'Bepul 🎉' if delivery_fee == 0 else f'{delivery_fee:,} UZS'}</b>")
    lines.append(f"<b>Jami to'lov: {grand_total:,} UZS</b>")

    from apps.accounts.models import TelegramUser
    tuser = await sync_to_async(lambda: TelegramUser.objects.filter(telegram_id=user_id).first())()
    if tuser and tuser.cashback_balance > 0:
        lines.append(f"\n✨ Sizda <b>{tuser.cashback_balance:,} UZS</b> keshbek bor!")

    text = "\n".join(lines)
    markup = cart_inline_keyboard(cart=cart, variants_dict=variants_dict)

    await safe_edit_message(callback.message, text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data == "clear_cart")
async def clear_bot_cart(callback: CallbackQuery):
    user_id = callback.from_user.id
    USER_CARTS[user_id] = {}
    USER_CARTS_DEAL_FLAGS[user_id] = False
    await callback.answer("🗑 Savat tozalandi", show_alert=True)
    await view_bot_cart(callback)


# ─── Checkout Flow inside Bot ─────────────────────────────────────────────────

@router.callback_query(F.data == "checkout_bot")
async def start_bot_checkout(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    cart = USER_CARTS.get(user_id, {})
    if not cart:
        await callback.answer("Savat bo'sh", show_alert=True)
        return

    await state.set_state(OrderState.waiting_for_phone)
    await callback.message.answer(
        "📱 <b>Buyurtmani rasmiylashtirish</b>\n\n"
        "Iltimos, bog'lanish uchun <b>telefon raqamingizni</b> yuboring 👇",
        parse_mode='HTML',
        reply_markup=request_phone_keyboard()
    )
    await callback.answer()


@router.message(OrderState.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    phone = ""
    if message.contact:
        phone = message.contact.phone_number
    elif message.text and message.text != "❌ Bekor qilish":
        phone = message.text.strip()
    else:
        await state.clear()
        await message.answer("Xarid bekor qilindi.", reply_markup=main_reply_keyboard())
        return

    await state.update_data(phone=phone)
    await state.set_state(OrderState.waiting_for_location)

    from asgiref.sync import sync_to_async
    from apps.accounts.models import Address

    user_id = message.from_user.id
    addresses = await sync_to_async(lambda: list(Address.objects.filter(user__telegram_id=user_id)))()

    if addresses:
        await message.answer(
            f"✅ Telefon: <b>{phone}</b>\n\n"
            "📍 <b>Saqlangan manzillaringizdan birini tanlang</b> yoki yangi manzil yuboring 👇",
            parse_mode='HTML',
            reply_markup=saved_addresses_keyboard(addresses)
        )
    else:
        await message.answer(
            f"✅ Telefon: <b>{phone}</b>\n\n"
            "📍 Endi yetkazib berish <b>manzilini</b> yuboring (Joylashuv tugmasini bosing yoki matn yozing) 👇",
            parse_mode='HTML',
            reply_markup=request_location_keyboard()
        )


async def _execute_order_creation(message: Message, state: FSMContext, address_text: str, user_obj):
    data = await state.get_data()
    phone = data.get('phone', '')
    user_id = user_obj.id
    cart = USER_CARTS.get(user_id, {})

    if not cart:
        await state.clear()
        await message.answer("Savat bo'sh qoldi.", reply_markup=main_reply_keyboard())
        return

    from asgiref.sync import sync_to_async
    from apps.accounts.models import TelegramUser, Address
    from apps.catalog.models import ProductVariant
    from apps.orders.models import Order, OrderItem, BankCard

    @sync_to_async
    def create_order_in_db():
        tuser, _ = TelegramUser.objects.get_or_create(
            telegram_id=user_id,
            defaults={'full_name': user_obj.full_name, 'phone': phone}
        )
        if phone:
            tuser.phone = phone
            tuser.save(update_fields=['phone'])

        addr_obj = Address.objects.create(user=tuser, address_text=address_text)

        variant_ids = list(cart.keys())
        variants = {v.id: v for v in ProductVariant.objects.filter(id__in=variant_ids).select_related('product')}

        order = Order.objects.create(
            user=tuser,
            address=addr_obj,
            payment_method='naqd',
            status='yangi',
            payment_status='pending'
        )

        subtotal = 0
        for vid, qty in cart.items():
            if vid in variants:
                v = variants[vid]
                item_total = v.price * qty
                subtotal += item_total
                OrderItem.objects.create(
                    order=order,
                    variant=v,
                    product_name_snapshot=v.product.name,
                    variant_weight_snapshot=v.label,
                    quantity=qty,
                    price_at_order=v.price
                )

        applied_promo_code = data.get('applied_promo_code')
        promo_discount_percent = data.get('promo_discount_percent', 0)

        if applied_promo_code and promo_discount_percent > 0:
            discount_amount = int(subtotal * promo_discount_percent / 100)
            subtotal = max(0, subtotal - discount_amount)
            from apps.orders.models import PromoCode
            promo_obj = PromoCode.objects.filter(code=applied_promo_code).first()
            if promo_obj:
                promo_obj.used_by_users.add(tuser)
                promo_obj.times_used += 1
                promo_obj.save(update_fields=['times_used'])

        fee = 0 if subtotal >= 150000 else 15000
        order.subtotal = subtotal
        order.delivery_fee = fee
        order.total = subtotal + fee
        order.save()
        return order

    try:
        order = await create_order_in_db()
        USER_CARTS[user_id] = {} # Clear cart
        PENDING_RECEIPT_ORDERS[user_id] = order.id
        await state.set_state(OrderState.waiting_for_receipt)

        card = await sync_to_async(lambda: BankCard.objects.filter(is_active=True).first())()
        bank_str = f"<b>{card.bank_name}</b>\n💳 Karta raqam: <code>{card.card_number}</code>\n👤 Egasi: <b>{card.card_holder}</b>" if card else "<b>Karta raqami:</b> <code>8600 1234 5678 9012</code>\n (Kapitalbank)"

        await message.answer(
            f"✅ <b>BUYURTMA #{order.id} YARATILDI!</b>\n\n"
            f"💰 Jami summa: <b>{order.total:,} UZS</b>\n\n"
            f"📌 <b>To'lov qilish uchun bank kartasi:</b>\n{bank_str}\n\n"
            f"📸 <b>To'lov qilgach, chek (skrinshot/foto) rasmini shu yerga yuboring!</b>",
            parse_mode='HTML',
            reply_markup=ReplyKeyboardRemove()
        )
    except Exception as e:
        logger.error("Create order error: %s", e)
        await state.clear()
        await message.answer("Buyurtma yaratishda xatolik yuz berdi. Qayta urining.", reply_markup=main_reply_keyboard())


@router.callback_query(F.data.startswith("use_addr:"))
async def handle_use_saved_address(callback: CallbackQuery, state: FSMContext):
    addr_id = int(callback.data.split(":")[1])
    from asgiref.sync import sync_to_async
    from apps.accounts.models import Address

    try:
        addr = await sync_to_async(Address.objects.get)(id=addr_id)
        await callback.message.answer(f"📍 Manzil tanlandi: <b>{addr.address_text}</b>", parse_mode='HTML')
        await _execute_order_creation(callback.message, state, addr.address_text, callback.from_user)
        await callback.answer()
    except Exception as err:
        logger.error("use_saved_address error: %s", err)
        await callback.answer("Manzil topilmadi", show_alert=True)


@router.callback_query(F.data == "new_addr")
async def handle_new_address(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "📍 Endi yetkazib berish <b>manzilini</b> yuboring (Joylashuv tugmasini bosing yoki matn yozing) 👇",
        parse_mode='HTML',
        reply_markup=request_location_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_order")
async def handle_cancel_order(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Xarid bekor qilindi.", reply_markup=main_reply_keyboard())
    await callback.answer()


@router.message(OrderState.waiting_for_location)
async def process_location(message: Message, state: FSMContext):
    if message.text in {"✏️ Manzilni matn qilib yozish", "Manzilni matn qilib yozish"}:
        await message.answer(
            "✍️ <b>Manzilingizni matn ko'rinishida yozib yuboring:</b>\n"
            "<i>(Masalan: Nurafshon sh., Navoiy ko'chasi 12-uy)</i>",
            parse_mode='HTML'
        )
        return

    address_text = ""
    if message.location:
        address_text = f"GPS: {message.location.latitude}, {message.location.longitude}"
    elif message.text and message.text != "❌ Bekor qilish":
        address_text = message.text.strip()
    else:
        await state.clear()
        await message.answer("Xarid bekor qilindi.", reply_markup=main_reply_keyboard())
        return

    await _execute_order_creation(message, state, address_text, message.from_user)


# ─── Payment Receipt Photo Handler ───────────────────────────────────────────

@router.message(OrderState.waiting_for_receipt)
@router.message(F.photo)
async def process_receipt_photo(message: Message, state: FSMContext):
    user_id = message.from_user.id
    order_id = PENDING_RECEIPT_ORDERS.get(user_id)

    if not message.photo and not message.document:
        await message.answer("Iltimos, to'lov cheki <b>rasmini (skrinshot)</b> yuboring 📸", parse_mode='HTML')
        return

    from asgiref.sync import sync_to_async
    from apps.orders.models import Order

    @sync_to_async
    def get_order():
        if order_id:
            try:
                return Order.objects.get(pk=order_id)
            except Order.DoesNotExist:
                pass
        return Order.objects.filter(user__telegram_id=user_id).order_by('-created_at').first()

    order = await get_order()
    if not order:
        await message.answer("Faol buyurtma topilmadi.", reply_markup=main_reply_keyboard())
        await state.clear()
        return

    try:
        # Download photo or document to media/payment_proofs/
        if message.photo:
            photo = message.photo[-1]
            file_id = photo.file_id
        else:
            file_id = message.document.file_id

        file_info = await message.bot.get_file(file_id)

        import os
        from django.conf import settings
        rel_dir = os.path.join('payment_proofs', order.created_at.strftime('%Y/%m'))
        abs_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)

        filename = f"order_{order.id}_{file_id[:8]}.jpg"
        abs_path = os.path.join(abs_dir, filename)
        rel_path = os.path.join(rel_dir, filename).replace('\\', '/')

        await message.bot.download_file(file_info.file_path, abs_path)

        @sync_to_async
        def save_proof():
            order.payment_proof = rel_path
            order.save(update_fields=['payment_proof'])
            return order

        await save_proof()
    except Exception as exc:
        logger.error("Save receipt error: %s", exc)

    await save_proof()

    PENDING_RECEIPT_ORDERS.pop(user_id, None)
    await state.clear()

    await message.answer(
        f"✅ <b>Chek qabul qilindi! (Buyurtma #{order.id})</b>\n\n"
        "Adminlarimiz to'lovni tekshirib, buyurtmangizni kuryerga berishadi. Rahmat! ☕",
        parse_mode='HTML',
        reply_markup=main_reply_keyboard()
    )

    # Notify admin with photo!
    from bot.notifications import notify_new_order
    import asyncio
    asyncio.create_task(notify_new_order(order.id))


# ─── Fast Re-order (Oxirgi buyurtmani takrorlash) ────────────────────────────

@router.message(F.text.in_({"🔄 Qayta buyurtma", "/reorder"}))
@router.callback_query(F.data == "reorder_last")
async def handle_fast_reorder(event: Message | CallbackQuery):
    user_id = event.from_user.id
    from asgiref.sync import sync_to_async
    from apps.orders.models import Order

    @sync_to_async
    def get_last_order():
        return Order.objects.filter(user__telegram_id=user_id).prefetch_related('items__variant').order_by('-created_at').first()

    order = await get_last_order()
    if not order or not order.items.exists():
        msg = "Sizda ilgari berilgan buyurtma topilmadi."
        if isinstance(event, CallbackQuery):
            await event.answer(msg, show_alert=True)
        else:
            await event.answer(msg)
        return

    # Put items into USER_CARTS
    USER_CARTS[user_id] = {}
    for item in order.items.all():
        if item.variant_id:
            USER_CARTS[user_id][item.variant_id] = item.quantity

    text = f"🔄 <b>#{order.id} buyurtmadagi mahsulotlar savatga qayta qo'shildi!</b>"
    markup = cart_inline_keyboard(has_items=True)

    if isinstance(event, CallbackQuery):
        await event.message.answer(text, parse_mode='HTML', reply_markup=markup)
        await event.answer()
    else:
        await event.answer(text, parse_mode='HTML', reply_markup=markup)


# ─── Do'kon / Aksiyalar / Buyurtmalar / Aloqa Command Handlers ────────────────

@router.message(Command("shop"))
@router.message(F.text == "🛍 Do'konni ochish (Web)")
async def cmd_shop(message: Message):
    await message.answer(
        "🛍 <b>Asl Nurafshon Do'koni</b>\n\nChoy va kofe tanlang 👇",
        parse_mode='HTML',
        reply_markup=shop_keyboard(settings.FRONTEND_URL),
    )


@router.message(Command("promo"))
@router.message(F.text == "🔥 Aksiyalar")
async def cmd_promo(message: Message):
    await message.answer(
        "🔥 <b>Bugungi aksiyalar va chegirmalar</b> 👇",
        parse_mode='HTML',
        reply_markup=promo_keyboard(settings.FRONTEND_URL),
    )


@router.message(Command("orders"))
@router.message(F.text == "📦 Buyurtmalarim")
async def cmd_orders(message: Message):
    from asgiref.sync import sync_to_async
    from apps.orders.models import Order

    orders = await sync_to_async(lambda: list(
        Order.objects.filter(user__telegram_id=message.from_user.id)
        .only('id', 'status', 'total', 'created_at')
        .order_by('-created_at')[:5]
    ))()

    if not orders:
        await message.answer(
            "📦 Buyurtmalaringiz hozircha yo'q.\n\nDo'kondan choy tanlang! 🛍",
            reply_markup=shop_keyboard(settings.FRONTEND_URL),
        )
        return

    lines = ["<b>📦 Oxirgi buyurtmalaringiz:</b>\n"]
    for o in orders:
        e = STATUS_EMOJI.get(o.status, '•')
        l = STATUS_LABEL.get(o.status, o.status)
        lines.append(f"{e} <b>#{o.id}</b> — {l}\n💰 {o.total:,} UZS | {o.created_at.strftime('%d.%m.%Y')}\n")

    await message.answer("\n".join(lines), parse_mode='HTML', reply_markup=orders_keyboard(settings.FRONTEND_URL))


@router.message(Command("contact"))
@router.message(F.text == "📞 Aloqa va Manzil")
async def cmd_contact(message: Message):
    await message.answer(CONTACT_TEXT, parse_mode='HTML')


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    await safe_edit_message(
        callback.message,
        "☕ <b>Asl Nurafshon</b>\n\nDo'konni ochish uchun bosing 👇",
        reply_markup=main_menu_keyboard(settings.FRONTEND_URL),
    )
    await callback.answer()


@router.callback_query(F.data == "contact")
async def cb_contact(callback: CallbackQuery):
    await safe_edit_message(callback.message, CONTACT_TEXT)
    await callback.answer()


@router.callback_query(F.data == "my_orders")
async def cb_my_orders(callback: CallbackQuery):
    await cmd_orders(callback.message)
    await callback.answer()


# ─── Admin status handlers ───────────────────────────────────────────────────

@router.callback_query(F.data.startswith("order:"))
async def handle_order_callback(callback: CallbackQuery):
    parts = callback.data.split(':')
    if len(parts) != 3:
        await callback.answer("Format xato")
        return

    _, action, order_id_str = parts
    try:
        order_id = int(order_id_str)
    except ValueError:
        await callback.answer("ID xato")
        return

    new_status = STATUS_MAP.get(action)
    if not new_status:
        await callback.answer("Noma'lum amal")
        return

    try:
        from asgiref.sync import sync_to_async
        from apps.orders.models import Order

        @sync_to_async
        def update_order():
            o = Order.objects.select_related('user').get(pk=order_id)
            old = o.status
            o.status = new_status
            if action == 'confirm':
                o.payment_status = 'paid'
            o.save(update_fields=['status', 'payment_status'])
            return o, old

        order, old_status = await update_order()
    except Exception:
        await callback.answer(f"#{order_id} topilmadi")
        return

    emoji = STATUS_EMOJI.get(new_status, '•')
    label = STATUS_LABEL.get(new_status, new_status)
    await callback.answer(f"{emoji} {label}")

    try:
        new_markup = _next_keyboard(order_id, new_status)
        await callback.message.edit_reply_markup(reply_markup=new_markup)
    except Exception:
        pass

    from bot.notifications import notify_status_change
    import asyncio
    asyncio.create_task(notify_status_change(order_id, new_status))


def _next_keyboard(order_id: int, status: str):
    if status == 'yolda':
        return order_delivered_keyboard(order_id)
    if status in ('yetkazildi', 'bekor_qilindi'):
        return None
    return order_admin_keyboard(order_id)
