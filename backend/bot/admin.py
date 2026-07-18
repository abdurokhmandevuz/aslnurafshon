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


def is_admin(telegram_id: int) -> bool:
    return telegram_id in settings.ADMIN_TELEGRAM_IDS


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Mahsulot qo'shish", callback_data='admin:product'),
            InlineKeyboardButton(text="Kunlik taklif", callback_data='admin:deal'),
        ],
        [
            InlineKeyboardButton(text="Combo yaratish", callback_data='admin:bundle'),
            InlineKeyboardButton(text="Bugungi hisobot", callback_data='admin:report'),
        ],
        [InlineKeyboardButton(text="Mijozlarga xabar", callback_data='admin:broadcast')],
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


@admin_router.callback_query(F.data == 'admin:deal')
async def deal_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.set_state(DealForm.search)
    await callback.message.answer("Kunlik taklif uchun mahsulot yoki variant nomini yozing.")
    await callback.answer()


async def _variant_choices(message: Message, state: FSMContext, prefix: str, query: str):
    from apps.catalog.models import ProductVariant
    variants = await sync_to_async(list)(
        ProductVariant.objects.filter(is_available=True, product__name__icontains=query)
        .select_related('product').order_by('product__name', 'price')[:8]
    )
    if not variants:
        await message.answer("Mos mahsulot topilmadi. Boshqa nom bilan qayta yuboring.")
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{item.product.name} - {item.label} ({item.price:,} UZS)", callback_data=f'{prefix}:{item.id}')]
        for item in variants
    ])
    await message.answer("Variantni tanlang.", reply_markup=keyboard)


@admin_router.message(DealForm.search)
async def deal_search(message: Message, state: FSMContext):
    await _variant_choices(message, state, 'admin:deal-variant', (message.text or '').strip())


@admin_router.callback_query(DealForm.search, F.data.startswith('admin:deal-variant:'))
async def deal_variant(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.update_data(variant_id=int(callback.data.rsplit(':', 1)[1]))
    await state.set_state(DealForm.discount)
    await callback.message.answer("Chegirma foizini yuboring: 1 dan 99 gacha.")
    await callback.answer()


@admin_router.message(DealForm.discount)
async def deal_discount(message: Message, state: FSMContext):
    discount = _parse_number(message.text or '')
    if discount is None or not 1 <= discount <= 99:
        await message.answer("Chegirma 1 dan 99 gacha bo'lishi kerak.")
        return
    data = await state.get_data()
    from apps.catalog.models import DailyDeal, ProductVariant

    @sync_to_async
    def save_deal():
        deal, _ = DailyDeal.objects.update_or_create(
            date=timezone.localdate(),
            defaults={'variant': ProductVariant.objects.get(pk=data['variant_id']), 'discount_percent': discount, 'is_active': True},
        )
        return deal

    deal = await save_deal()
    await state.clear()
    await message.answer(f"Bugungi taklif saqlandi: <b>{deal.variant}</b> (-{discount}%).", parse_mode='HTML', reply_markup=admin_menu())


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
