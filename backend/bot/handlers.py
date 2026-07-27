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
    waiting_for_phone = State()
    waiting_for_location = State()
    waiting_for_receipt = State()


# In-memory user cart storage: { user_id: { variant_id: quantity } }
USER_CARTS = {}
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

    await message.answer(
        f"Assalomu alaykum, <b>{user.first_name}</b>! 👋\n\n"
        "☕ <b>Asl Nurafshon</b> — premium choy va kofe do'koniga xush kelibsiz!\n\n"
        "Quyidagi tugmalar orqali xarid qilishingiz mumkin 👇",
        parse_mode='HTML',
        reply_markup=main_reply_keyboard(),
    )
    await message.answer(
        "Do'kon menusi:",
        parse_mode='HTML',
        reply_markup=main_menu_keyboard(settings.FRONTEND_URL),
    )


# ─── Bot Catalog Browsing ─────────────────────────────────────────────────────

@router.message(F.text.in_({"☕ Choy tanlash (Bot)", "☕ Bot Katalogi", "/catalog"}))
@router.callback_query(F.data == "bot_catalog")
async def show_bot_catalog(event: Message | CallbackQuery):
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


# ─── View Cart ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "view_cart")
async def view_bot_cart(callback: CallbackQuery):
    user_id = callback.from_user.id
    cart = USER_CARTS.get(user_id, {})

    if not cart:
        await safe_edit_message(
            callback.message,
            "🛒 <b>Savatingiz bo'sh.</b>\n\nKatalogdan mahsulotlarni tanlang!",
            reply_markup=cart_inline_keyboard(has_items=False)
        )
        await callback.answer()
        return

    from asgiref.sync import sync_to_async
    from apps.catalog.models import ProductVariant

    variant_ids = list(cart.keys())
    variants = await sync_to_async(lambda: list(ProductVariant.objects.filter(id__in=variant_ids).select_related('product')))()

    total_sum = 0
    lines = ["🛒 <b>Savatdagi mahsulotlar:</b>\n"]

    for v in variants:
        qty = cart[v.id]
        item_total = v.price * qty
        total_sum += item_total
        lines.append(f"• <b>{v.product.name}</b> ({v.label})\n  {qty} ta × {v.price:,} = <b>{item_total:,} UZS</b>")

    delivery_fee = 0 if total_sum >= 150000 else 15000
    grand_total = total_sum + delivery_fee

    lines.append(f"\nMahsulotlar: <b>{total_sum:,} UZS</b>")
    lines.append(f"Yetkazib berish: <b>{'Bepul 🎉' if delivery_fee == 0 else f'{delivery_fee:,} UZS'}</b>")
    lines.append(f"<b>Jami to'lov: {grand_total:,} UZS</b>")

    text = "\n".join(lines)
    markup = cart_inline_keyboard(has_items=True)

    await safe_edit_message(callback.message, text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data == "clear_cart")
async def clear_bot_cart(callback: CallbackQuery):
    user_id = callback.from_user.id
    USER_CARTS[user_id] = {}
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
    await message.answer(
        f"✅ Telefon: <b>{phone}</b>\n\n"
        "📍 Endi yetkazib berish <b>manzilini</b> yuboring (Joylashuv tugmasini bosing yoki matn yozing) 👇",
        parse_mode='HTML',
        reply_markup=request_location_keyboard()
    )


@router.message(OrderState.waiting_for_location)
async def process_location(message: Message, state: FSMContext):
    address_text = ""
    if message.location:
        address_text = f"GPS: {message.location.latitude}, {message.location.longitude}"
    elif message.text and message.text != "❌ Bekor qilish":
        address_text = message.text.strip()
    else:
        await state.clear()
        await message.answer("Xarid bekor qilindi.", reply_markup=main_reply_keyboard())
        return

    data = await state.get_data()
    phone = data.get('phone', '')
    user_id = message.from_user.id
    cart = USER_CARTS.get(user_id, {})

    if not cart:
        await state.clear()
        await message.answer("Savat bo'sh qoldi.", reply_markup=main_reply_keyboard())
        return

    # Create Order in DB
    from asgiref.sync import sync_to_async
    from apps.accounts.models import TelegramUser, Address
    from apps.catalog.models import ProductVariant
    from apps.orders.models import Order, OrderItem, BankCard

    @sync_to_async
    def create_order_in_db():
        tuser, _ = TelegramUser.objects.get_or_create(
            telegram_id=user_id,
            defaults={'full_name': message.from_user.full_name, 'phone': phone}
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

        # Get Bank card info
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


# ─── Payment Receipt Photo Handler ───────────────────────────────────────────

@router.message(F.photo | OrderState.waiting_for_receipt)
async def process_receipt_photo(message: Message, state: FSMContext):
    user_id = message.from_user.id
    order_id = PENDING_RECEIPT_ORDERS.get(user_id)

    if not message.photo:
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

    # Download photo to media/payment_proofs/
    photo = message.photo[-1]
    file_info = await message.bot.get_file(photo.file_id)

    import os
    from django.conf import settings
    rel_dir = os.path.join('payment_proofs', order.created_at.strftime('%Y/%m'))
    abs_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)

    filename = f"order_{order.id}_{photo.file_id[:8]}.jpg"
    abs_path = os.path.join(abs_dir, filename)
    rel_path = os.path.join(rel_dir, filename).replace('\\', '/')

    await message.bot.download_file(file_info.file_path, abs_path)

    @sync_to_async
    def save_proof():
        order.payment_proof = rel_path
        order.save(update_fields=['payment_proof'])
        return order

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
