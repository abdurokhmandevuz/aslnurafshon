"""Private, Telegram-ID protected admin controls for the shop bot."""
import asyncio
import io
import logging
import uuid

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

logger = logging.getLogger(__name__)
admin_router = Router(name='admin')


class ProductForm(StatesGroup):
    photo = State()
    name = State()
    category = State()
    variant_label = State()
    price = State()
    stock = State()


class DealForm(StatesGroup):
    search = State()
    discount = State()


class BundleForm(StatesGroup):
    photo = State()
    name = State()
    description = State()
    discount = State()
    search = State()
    quantity = State()
    action = State()


class BroadcastForm(StatesGroup):
    text = State()
    confirm = State()


class PromoCodeForm(StatesGroup):
    code = State()
    discount_percent = State()


class CardForm(StatesGroup):
    bank_name = State()
    card_number = State()
    card_holder = State()


class DealWizardForm(StatesGroup):
    selecting_variants = State()
    photo = State()
    delivery_fee = State()
    discount = State()
    duration = State()
    confirm = State()


def is_admin(telegram_id: int) -> bool:
    return telegram_id in settings.ADMIN_TELEGRAM_IDS


def admin_menu() -> InlineKeyboardMarkup:
    web_admin_url = "https://aslnurafshon.up.railway.app/admin/"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Mahsulot qo'shish", callback_data='admin:product'),
            InlineKeyboardButton(text="🔥 Kunlik taklif", callback_data='admin:deal'),
        ],
        [
            InlineKeyboardButton(text="🎁 Promo-kod yaratish", callback_data='admin:promocode'),
            InlineKeyboardButton(text="💳 Karta sozlamalari", callback_data='admin:card'),
        ],
        [
            InlineKeyboardButton(text="📊 Bugungi hisobot", callback_data='admin:report'),
            InlineKeyboardButton(text="📢 Mijozlarga xabar", callback_data='admin:broadcast'),
        ],
        [
            InlineKeyboardButton(text="🌐 Veb Admin Panel", url=web_admin_url),
        ],
    ])


def _is_admin_message(message: Message) -> bool:
    return bool(message.from_user and is_admin(message.from_user.id))


async def _deny(message: Message | CallbackQuery):
    if isinstance(message, CallbackQuery):
        await message.answer("Bu boshqaruv paneliga ruxsatingiz yo'q.", show_alert=True)
    else:
        await message.answer("Bu buyruq faqat admin uchun.")


async def _save_photo(message: Message) -> ContentFile | None:
    if not message.photo:
        return None
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    buffer = io.BytesIO()
    await message.bot.download_file(file.file_path, destination=buffer)
    return ContentFile(buffer.getvalue(), name=f"bot-{uuid.uuid4().hex}.jpg")


def _parse_number(value: str) -> int | None:
    cleaned = value.replace(' ', '').replace(',', '')
    try:
        number = int(cleaned)
    except ValueError:
        return None
    return number if number >= 0 else None


@admin_router.message(Command('id'))
async def chat_id(message: Message):
    await message.answer(f"Sizning chat ID: <code>{message.chat.id}</code>", parse_mode='HTML')


@admin_router.message(Command('admin'))
async def admin_start(message: Message, state: FSMContext):
    if not _is_admin_message(message):
        await _deny(message)
        return
    await state.clear()
    await message.answer("<b>Admin panel</b>\nKerakli amalni tanlang.", parse_mode='HTML', reply_markup=admin_menu())


@admin_router.callback_query(F.data == 'admin:home')
async def admin_home(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.clear()
    await callback.message.answer("<b>Admin panel</b>", parse_mode='HTML', reply_markup=admin_menu())
    await callback.answer()


@admin_router.callback_query(F.data == 'admin:product')
async def product_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.set_state(ProductForm.photo)
    await callback.message.answer("Mahsulot rasmini yuboring. Rasm bo'lmasa <code>-</code> yuboring.", parse_mode='HTML')
    await callback.answer()


@admin_router.message(ProductForm.photo)
async def product_photo(message: Message, state: FSMContext):
    if not _is_admin_message(message):
        await _deny(message)
        return
    photo = await _save_photo(message)
    if photo is None and (message.text or '').strip() != '-':
        await message.answer("Rasm yuboring yoki rasm qo'shmaslik uchun <code>-</code> yuboring.", parse_mode='HTML')
        return
    await state.update_data(photo=photo)
    await state.set_state(ProductForm.name)
    await message.answer("Mahsulot nomini yuboring.")


@admin_router.message(ProductForm.name)
async def product_name(message: Message, state: FSMContext):
    name = (message.text or '').strip()
    if not name:
        await message.answer("Mahsulot nomini matn ko'rinishida yuboring.")
        return
    await state.update_data(name=name)

    from apps.catalog.models import Category
    categories = await sync_to_async(list)(Category.objects.filter(is_active=True).order_by('order', 'name'))
    if not categories:
        await state.clear()
        await message.answer("Avval Django admin orqali kamida bitta kategoriya yarating.")
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=category.name, callback_data=f'admin:product-category:{category.id}')]
        for category in categories
    ])
    await state.set_state(ProductForm.category)
    await message.answer("Kategoriyani tanlang.", reply_markup=keyboard)


@admin_router.callback_query(ProductForm.category, F.data.startswith('admin:product-category:'))
async def product_category(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.update_data(category_id=int(callback.data.rsplit(':', 1)[1]))
    await state.set_state(ProductForm.variant_label)
    await callback.message.answer("Variant nomini yuboring. Masalan: <code>100 gr</code> yoki <code>1 dona</code>.", parse_mode='HTML')
    await callback.answer()


@admin_router.message(ProductForm.variant_label)
async def product_variant_label(message: Message, state: FSMContext):
    label = (message.text or '').strip()
    if not label:
        await message.answer("Variant nomini yuboring.")
        return
    await state.update_data(variant_label=label)
    await state.set_state(ProductForm.price)
    await message.answer("Narxini faqat son bilan yuboring. Masalan: <code>15000</code>", parse_mode='HTML')


@admin_router.message(ProductForm.price)
async def product_price(message: Message, state: FSMContext):
    price = _parse_number(message.text or '')
    if price is None or price == 0:
        await message.answer("Narx 0 dan katta son bo'lishi kerak.")
        return
    await state.update_data(price=price)
    await state.set_state(ProductForm.stock)
    await message.answer("Ombordagi sonini yuboring. Masalan: <code>20</code>", parse_mode='HTML')


@admin_router.message(ProductForm.stock)
async def product_stock(message: Message, state: FSMContext):
    stock = _parse_number(message.text or '')
    if stock is None:
        await message.answer("Qoldiqni 0 yoki undan katta son bilan yuboring.")
        return
    data = await state.get_data()
    from apps.catalog.models import Category, Product, ProductVariant

    @sync_to_async
    def create_product():
        product = Product.objects.create(
            category=Category.objects.get(pk=data['category_id']),
            name=data['name'],
            image=data.get('photo'),
        )
        variant = ProductVariant.objects.create(
            product=product,
            label=data['variant_label'],
            price=data['price'],
            stock_qty=stock,
            is_available=stock > 0,
            is_default=True,
        )
        return product, variant

    product, variant = await create_product()
    await state.clear()
    await message.answer(
        f"Mahsulot qo'shildi.\n\n<b>{product.name}</b>\n{variant.label} - {variant.price:,} UZS\nQoldiq: {variant.stock_qty}",
        parse_mode='HTML', reply_markup=admin_menu(),
    )


# ─── Daily Deal Wizard Handlers ──────────────────────────────────────────────

@admin_router.callback_query(F.data == 'admin:deal')
async def deal_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.clear()
    await state.set_state(DealWizardForm.selecting_variants)
    await state.update_data(selected_ids=[])
    await render_deal_variant_selection(callback, state)


async def render_deal_variant_selection(event: Message | CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_ids = set(data.get('selected_ids', []))

    from apps.catalog.models import ProductVariant
    variants = await sync_to_async(list)(
        ProductVariant.objects.filter(is_available=True)
        .select_related('product').order_by('product__name', 'price')[:30]
    )

    if not variants:
        msg = "Hali faol mahsulotlar yo'q. Avval mahsulot qo'shing."
        if isinstance(event, CallbackQuery):
            await event.message.answer(msg)
            await event.answer()
        else:
            await event.answer(msg)
        return

    buttons = []
    for item in variants:
        is_sel = item.id in selected_ids
        icon = "✅" if is_sel else "❌"
        btn_text = f"{icon} {item.product.name} ({item.label}) — {item.price:,} UZS"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f'admin:deal-toggle:{item.id}')])

    sel_count = len(selected_ids)
    if sel_count > 0:
        buttons.append([InlineKeyboardButton(text=f"➡️ Keyingi bosqich ({sel_count} ta tanlandi)", callback_data='admin:deal-next')])
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data='admin:home')])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    text = (
        "<b>🔥 Kunlik taklif uchun mahsulotlarni tanlang:</b>\n\n"
        "Mahsulot ustiga bosib ptichka <b>(✅)</b> qo'ying. "
        "Bir nechta tanlashingiz mumkin. Yakunlash uchun <i>Keyingi bosqich</i> tugmasini bosing 👇"
    )

    if isinstance(event, CallbackQuery):
        await safe_edit_message(event.message, text, reply_markup=keyboard)
        await event.answer()
    else:
        await event.answer(text, parse_mode='HTML', reply_markup=keyboard)


@admin_router.callback_query(DealWizardForm.selecting_variants, F.data.startswith('admin:deal-toggle:'))
async def deal_toggle_variant(callback: CallbackQuery, state: FSMContext):
    var_id = int(callback.data.split(':')[-1])
    data = await state.get_data()
    selected_ids = set(data.get('selected_ids', []))

    if var_id in selected_ids:
        selected_ids.remove(var_id)
    else:
        selected_ids.add(var_id)

    await state.update_data(selected_ids=list(selected_ids))
    await render_deal_variant_selection(callback, state)


@admin_router.callback_query(DealWizardForm.selecting_variants, F.data == 'admin:deal-next')
async def deal_next_to_photo(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get('selected_ids'):
        await callback.answer("Kamida 1 ta mahsulot tanlang!", show_alert=True)
        return

    await state.set_state(DealWizardForm.photo)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⏭ Rasmsiz davom etish", callback_data='admin:deal-skip-photo')
    ]])
    await callback.message.answer(
        "📸 <b>Kunlik taklif uchun rasm yuklang:</b>\n\n"
        "Rasmni shu yerga yuboring yoki rasm qo'shmaslik uchun tugmani bosing 👇",
        parse_mode='HTML',
        reply_markup=keyboard
    )
    await callback.answer()


@admin_router.message(DealWizardForm.photo, F.photo)
@admin_router.callback_query(DealWizardForm.photo, F.data == 'admin:deal-skip-photo')
async def deal_process_photo(event: Message | CallbackQuery, state: FSMContext):
    photo_id = None
    if isinstance(event, Message) and event.photo:
        photo_id = event.photo[-1].file_id
        msg = event
    else:
        msg = event.message
        await event.answer()

    await state.update_data(photo_id=photo_id)
    await state.set_state(DealWizardForm.delivery_fee)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⏭ O'tkazib yuborish (15,000 UZS)", callback_data='admin:deal-skip-delivery')
    ]])
    await msg.answer(
        "🚚 <b>Dastavka narxini kiriting (UZS):</b>\n\n"
        "<i>(Masalan: 10000 yoki 0 - bepul)</i>\n\n"
        "Standart 15,000 UZS bo'lib qolishi uchun tugmani bosing 👇",
        parse_mode='HTML',
        reply_markup=keyboard
    )


@admin_router.message(DealWizardForm.delivery_fee)
@admin_router.callback_query(DealWizardForm.delivery_fee, F.data == 'admin:deal-skip-delivery')
async def deal_process_delivery(event: Message | CallbackQuery, state: FSMContext):
    fee = 15000
    if isinstance(event, Message):
        val = _parse_number(event.text or '')
        if val is not None:
            fee = val
        msg = event
    else:
        msg = event.message
        await event.answer()

    await state.update_data(delivery_fee=fee)
    await state.set_state(DealWizardForm.discount)
    await msg.answer("🏷 <b>Chegirma foizini kiriting (1 dan 99 gacha):</b>\n<i>(Masalan: 20)</i>", parse_mode='HTML')


@admin_router.message(DealWizardForm.discount)
async def deal_process_discount(message: Message, state: FSMContext):
    discount = _parse_number(message.text or '')
    if discount is None or not 1 <= discount <= 99:
        await message.answer("Chegirma foizi 1 dan 99 gacha son bo'lishi kerak.")
        return

    await state.update_data(discount_percent=discount)
    await state.set_state(DealWizardForm.duration)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⏭ O'tkazib yuborish (24 soat)", callback_data='admin:deal-skip-duration')
    ]])
    await message.answer(
        "⏰ <b>Kunlik taklif amal qilish vaqtini kiriting (soatda):</b>\n\n"
        "<i>(Masalan: 12 yoki 24 yoki 48)</i>\n\n"
        "Standart 24 soat bo'lib qolishi uchun tugmani bosing 👇",
        parse_mode='HTML',
        reply_markup=keyboard
    )


@admin_router.message(DealWizardForm.duration)
@admin_router.callback_query(DealWizardForm.duration, F.data == 'admin:deal-skip-duration')
async def deal_process_duration(event: Message | CallbackQuery, state: FSMContext):
    hours = 24
    if isinstance(event, Message):
        val = _parse_number(event.text or '')
        if val is not None and val > 0:
            hours = val
        msg = event
    else:
        msg = event.message
        await event.answer()

    await state.update_data(duration_hours=hours)
    await state.set_state(DealWizardForm.confirm)

    data = await state.get_data()
    selected_ids = data.get('selected_ids', [])
    discount = data.get('discount_percent', 0)
    fee = data.get('delivery_fee', 15000)

    from apps.catalog.models import ProductVariant
    variants = await sync_to_async(list)(
        ProductVariant.objects.filter(id__in=selected_ids).select_related('product')
    )

    lines = ["<b>🔥 KUNLIK TAKLIF KONSEPSIYASI VA HISOB-KITOBLARI:</b>\n"]
    for idx, v in enumerate(variants, 1):
        deal_price = int(v.price * (100 - discount) / 100)
        total_with_del = deal_price + fee
        lines.append(
            f"<b>{idx}. {v.product.name}</b> ({v.label})\n"
            f"  • Asl narxi: <s>{v.price:,} UZS</s>\n"
            f"  • Chegirmali narx (-{discount}%): <b>{deal_price:,} UZS</b>\n"
            f"  • Dastavka narxi: <b>{fee:,} UZS</b>\n"
            f"  • Jami (1 ta uchun): <b>{total_with_del:,} UZS</b>\n"
        )

    lines.append(f"⏰ Amal qilish muddati: <b>{hours} soat</b>")
    lines.append(f"📸 Rasm: <b>{'Yuklangan ✅' if data.get('photo_id') else 'Mavjud emas ❌'}</b>\n")
    lines.append("Mijozlarga e'lon qilishni tasdiqlaysizmi? 👇")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Mijozlarga e'lon qilish (Avto-yuborish)", callback_data='admin:deal-broadcast')],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data='admin:home')]
    ])

    await msg.answer("\n".join(lines), parse_mode='HTML', reply_markup=keyboard)


@admin_router.callback_query(DealWizardForm.confirm, F.data == 'admin:deal-broadcast')
async def deal_broadcast_confirm(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return

    data = await state.get_data()
    selected_ids = data.get('selected_ids', [])
    discount = data.get('discount_percent', 0)
    fee = data.get('delivery_fee', 15000)
    hours = data.get('duration_hours', 24)
    photo_id = data.get('photo_id')

    from apps.catalog.models import DailyDeal, ProductVariant
    from apps.accounts.models import TelegramUser
    from django.utils import timezone
    import datetime

    ends_at = timezone.now() + datetime.timedelta(hours=hours)

    @sync_to_async
    def create_deals_in_db():
        created_deals = []
        for vid in selected_ids:
            variant = ProductVariant.objects.get(id=vid)
            deal = DailyDeal.objects.create(
                variant=variant,
                discount_percent=discount,
                delivery_fee=fee,
                starts_at=timezone.now(),
                ends_at=ends_at,
                is_active=True
            )
            created_deals.append(deal)
        return created_deals

    deals = await create_deals_in_db()
    await state.clear()

    # Broadcast to all users
    users = await sync_to_async(list)(TelegramUser.objects.values_list('telegram_id', flat=True))
    sent_count = 0

    for deal in deals:
        v = deal.variant
        deal_price = deal.deal_price
        caption = (
            f"🔥 <b>KUNLIK MAXSUS TAKLIF!</b> 🔥\n\n"
            f"☕ <b>{v.product.name}</b> ({v.label})\n"
            f"<s>{v.price:,} UZS</s> ➡️ <b>{deal_price:,} UZS</b> (-{discount}%)\n"
            f"🚚 Dastavka: <b>{'Bepul 🎉' if fee == 0 else f'{fee:,} UZS'}</b>\n"
            f"⏰ Amal qilish vaqti: <b>{hours} soat</b>\n\n"
            f"⚡️ Shoshiling, eng sifatli mahsulotlar chegirmada!"
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🛒 Savatga qo'shish (Xarid)", callback_data=f"add_deal:{deal.id}")
        ]])

        for u_id in users:
            try:
                if photo_id:
                    await callback.bot.send_photo(u_id, photo_id, caption=caption, parse_mode='HTML', reply_markup=markup)
                else:
                    await callback.bot.send_message(u_id, caption, parse_mode='HTML', reply_markup=markup)
                sent_count += 1
                await asyncio.sleep(0.04)
            except Exception:
                pass

    await callback.message.answer(
        f"✅ <b>Kunlik taklif saqlandi!</b>\n\nJami {len(deals)} ta mahsulot {sent_count} ta mijozga e'lon qilindi.",
        parse_mode='HTML',
        reply_markup=admin_menu()
    )
    await callback.answer()


@admin_router.callback_query(F.data == 'admin:bundle')
async def bundle_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.set_state(BundleForm.photo)
    await callback.message.answer("Combo uchun rasm yuboring.")
    await callback.answer()


@admin_router.message(BundleForm.photo)
async def bundle_photo(message: Message, state: FSMContext):
    if not _is_admin_message(message):
        await _deny(message)
        return
    photo = await _save_photo(message)
    if photo is None:
        await message.answer("Combo uchun rasm yuboring.")
        return
    await state.update_data(photo=photo)
    await state.set_state(BundleForm.name)
    await message.answer("Combo nomini yuboring.")


@admin_router.message(BundleForm.name)
async def bundle_name(message: Message, state: FSMContext):
    name = (message.text or '').strip()
    if not name:
        await message.answer("Combo nomini yuboring.")
        return
    await state.update_data(name=name)
    await state.set_state(BundleForm.description)
    await message.answer("Qisqa tavsifini yuboring. Tavsifsiz bo'lsa <code>-</code> yuboring.", parse_mode='HTML')


@admin_router.message(BundleForm.description)
async def bundle_description(message: Message, state: FSMContext):
    description = (message.text or '').strip()
    await state.update_data(description='' if description == '-' else description)
    await state.set_state(BundleForm.discount)
    await message.answer("Combo chegirmasini yuboring: 0 dan 99 gacha.")


@admin_router.message(BundleForm.discount)
async def bundle_discount(message: Message, state: FSMContext):
    discount = _parse_number(message.text or '')
    if discount is None or discount > 99:
        await message.answer("Chegirma 0 dan 99 gacha bo'lishi kerak.")
        return
    data = await state.get_data()
    from apps.catalog.models import ProductBundle

    @sync_to_async
    def create_bundle():
        return ProductBundle.objects.create(
            name=data['name'],
            slug=f"bot-combo-{uuid.uuid4().hex[:12]}",
            description=data['description'],
            discount_percent=discount,
            image=data['photo'],
        )

    bundle = await create_bundle()
    await state.update_data(bundle_id=bundle.id)
    await state.set_state(BundleForm.search)
    await message.answer("Combo ichiga qo'shiladigan mahsulot nomini yozing.")


@admin_router.message(BundleForm.search)
async def bundle_search(message: Message, state: FSMContext):
    await _variant_choices(message, state, 'admin:bundle-variant', (message.text or '').strip())


@admin_router.callback_query(BundleForm.search, F.data.startswith('admin:bundle-variant:'))
async def bundle_variant(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.update_data(variant_id=int(callback.data.rsplit(':', 1)[1]))
    await state.set_state(BundleForm.quantity)
    await callback.message.answer("Shu mahsulotdan nechta qo'shiladi? Masalan: <code>2</code>", parse_mode='HTML')
    await callback.answer()


@admin_router.message(BundleForm.quantity)
async def bundle_quantity(message: Message, state: FSMContext):
    quantity = _parse_number(message.text or '')
    if quantity is None or quantity == 0:
        await message.answer("Miqdor 0 dan katta son bo'lishi kerak.")
        return
    data = await state.get_data()
    from apps.catalog.models import BundleItem

    @sync_to_async
    def add_item():
        item, created = BundleItem.objects.get_or_create(
            bundle_id=data['bundle_id'],
            variant_id=data['variant_id'],
            defaults={'quantity': quantity},
        )
        if not created:
            item.quantity += quantity
            item.save(update_fields=['quantity'])

    await add_item()
    await state.set_state(BundleForm.action)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Yana mahsulot qo'shish", callback_data='admin:bundle-more'),
        InlineKeyboardButton(text="Combo saqlash", callback_data='admin:bundle-finish'),
    ]])
    await message.answer("Mahsulot combo tarkibiga qo'shildi.", reply_markup=keyboard)


@admin_router.callback_query(BundleForm.action, F.data == 'admin:bundle-more')
async def bundle_more(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.set_state(BundleForm.search)
    await callback.message.answer("Keyingi mahsulot nomini yozing.")
    await callback.answer()


@admin_router.callback_query(BundleForm.action, F.data == 'admin:bundle-finish')
async def bundle_finish(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    data = await state.get_data()
    from apps.catalog.models import ProductBundle
    bundle = await sync_to_async(ProductBundle.objects.get)(pk=data['bundle_id'])
    await state.clear()
    await callback.message.answer(
        f"Combo saqlandi.\n\n<b>{bundle.name}</b>\nNarxi: <b>{bundle.price:,} UZS</b>",
        parse_mode='HTML', reply_markup=admin_menu(),
    )
    await callback.answer()


@admin_router.callback_query(F.data == 'admin:report')
async def admin_report(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    from apps.accounts.models import TelegramUser
    from apps.orders.models import Order

    @sync_to_async
    def report_data():
        today = timezone.localdate()
        orders = Order.objects.filter(created_at__date=today)
        return orders.count(), sum(order.total for order in orders), TelegramUser.objects.count()

    order_count, revenue, customer_count = await report_data()
    await callback.message.answer(
        f"<b>Bugungi hisobot</b>\n\nBuyurtmalar: <b>{order_count}</b>\nSavdo: <b>{revenue:,} UZS</b>\nMijozlar: <b>{customer_count}</b>",
        parse_mode='HTML', reply_markup=admin_menu(),
    )
    await callback.answer()


@admin_router.callback_query(F.data == 'admin:broadcast')
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.set_state(BroadcastForm.text)
    await callback.message.answer("Mijozlarga yuboriladigan xabarni yozing. Bekor qilish uchun /admin yuboring.")
    await callback.answer()


@admin_router.message(BroadcastForm.text)
async def broadcast_text(message: Message, state: FSMContext):
    text = (message.text or '').strip()
    if not text:
        await message.answer("Faqat matnli xabar yuboring.")
        return
    await state.update_data(text=text)
    await state.set_state(BroadcastForm.confirm)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Yuborish", callback_data='admin:broadcast-send'),
        InlineKeyboardButton(text="Bekor qilish", callback_data='admin:home'),
    ]])
    await message.answer(f"<b>Yuboriladigan xabar:</b>\n\n{text}", parse_mode='HTML', reply_markup=keyboard)


@admin_router.callback_query(BroadcastForm.confirm, F.data == 'admin:broadcast-send')
async def broadcast_send(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    data = await state.get_data()
    from apps.accounts.models import TelegramUser
    telegram_ids = await sync_to_async(list)(TelegramUser.objects.values_list('telegram_id', flat=True))
    sent = 0
    for telegram_id in telegram_ids:
        try:
            await callback.bot.send_message(telegram_id, data['text'])
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            logger.info('Broadcast skipped Telegram user %s', telegram_id)
    await state.clear()
    await callback.message.answer(f"Xabar {sent} ta mijozga yuborildi.", reply_markup=admin_menu())
    await callback.answer()


# ─── PromoCode & Card Handlers ───────────────────────────────────────────────

@admin_router.callback_query(F.data == 'admin:promocode')
async def promocode_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.set_state(PromoCodeForm.code)
    await callback.message.answer("<b>🎁 Yangi Promo-kod yaratish</b>\n\nPromo-kod matnini yuboring (masalan: <code>NURAFSHON10</code>):", parse_mode='HTML')
    await callback.answer()


@admin_router.message(PromoCodeForm.code)
async def promocode_code(message: Message, state: FSMContext):
    if not _is_admin_message(message):
        await _deny(message)
        return
    code_text = (message.text or '').strip().upper()
    if not code_text:
        await message.answer("Promo-kod matnini yuboring.")
        return
    await state.update_data(code=code_text)
    await state.set_state(PromoCodeForm.discount_percent)
    await message.answer("Chegirma foizini yuboring (masalan: <code>10</code>):", parse_mode='HTML')


@admin_router.message(PromoCodeForm.discount_percent)
async def promocode_discount(message: Message, state: FSMContext):
    discount = _parse_number(message.text or '')
    if discount is None or not 1 <= discount <= 99:
        await message.answer("Chegirma foizi 1 dan 99 gacha son bo'lishi kerak.")
        return
    data = await state.get_data()
    from apps.orders.models import PromoCode
    import datetime

    @sync_to_async
    def create_promo():
        promo, _ = PromoCode.objects.update_or_create(
            code=data['code'],
            defaults={
                'discount_percent': discount,
                'valid_until': timezone.now() + datetime.timedelta(days=365),
                'usage_limit': 1000,
                'is_active': True,
            }
        )
        return promo

    promo = await create_promo()
    await state.clear()
    await message.answer(f"✅ Promo-kod yaratildi: <b>{promo.code}</b> (-{discount}%)", parse_mode='HTML', reply_markup=admin_menu())


@admin_router.callback_query(F.data == 'admin:card')
async def card_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.set_state(CardForm.bank_name)
    await callback.message.answer("<b>💳 Bank kartasini kiritish</b>\n\nBank nomini yuboring (masalan: <code>Kapitalbank</code>):", parse_mode='HTML')
    await callback.answer()


@admin_router.message(CardForm.bank_name)
async def card_bank_name(message: Message, state: FSMContext):
    bank_name = (message.text or '').strip()
    if not bank_name:
        await message.answer("Bank nomini yuboring.")
        return
    await state.update_data(bank_name=bank_name)
    await state.set_state(CardForm.card_number)
    await message.answer("Karta raqamini yuboring (masalan: <code>8600 1234 5678 9012</code>):", parse_mode='HTML')


@admin_router.message(CardForm.card_number)
async def card_number(message: Message, state: FSMContext):
    card_num = (message.text or '').strip()
    if not card_num:
        await message.answer("Karta raqamini yuboring.")
        return
    await state.update_data(card_number=card_num)
    await state.set_state(CardForm.card_holder)
    await message.answer("Karta egasining ismini yuboring (masalan: <code>ASL NURAFSHON MCHJ</code>):", parse_mode='HTML')


@admin_router.message(CardForm.card_holder)
async def card_holder(message: Message, state: FSMContext):
    holder = (message.text or '').strip()
    if not holder:
        await message.answer("Karta egasini yuboring.")
        return
    data = await state.get_data()
    from apps.orders.models import BankCard

    @sync_to_async
    def save_card():
        BankCard.objects.all().update(is_active=False)
        card = BankCard.objects.create(
            bank_name=data['bank_name'],
            card_number=data['card_number'],
            card_holder=holder,
            is_active=True
        )
        return card

    card = await save_card()
    await state.clear()
    await message.answer(
        f"✅ Yangi to'lov kartasi o'rnatildi!\n\n"
        f"🏦 Bank: <b>{card.bank_name}</b>\n"
        f"💳 Karta: <code>{card.card_number}</code>\n"
        f"👤 Egasi: <b>{card.card_holder}</b>",
        parse_mode='HTML',
        reply_markup=admin_menu()
    )
