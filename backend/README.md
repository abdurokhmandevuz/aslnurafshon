# Nurafshon Backend

Django 5 + DRF backend for the Nurafshon tea/coffee Telegram Mini App.

## Stack

| Component | Technology |
|-----------|-----------|
| Framework | Django 5.x + Django REST Framework |
| Auth | Telegram WebApp initData (HMAC-SHA256) |
| Database | PostgreSQL (Railway) / SQLite (local) |
| Bot | aiogram 3.x |
| Payments | Payme + Click (mock mode by default) |
| Deploy | Railway (web + bot via Procfile) |

---

## Project Structure

```
backend/
├── config/
│   ├── settings/
│   │   ├── base.py         # Shared settings
│   │   ├── local.py        # Dev (SQLite fallback, CORS allow all)
│   │   └── production.py   # Railway (PostgreSQL, HTTPS)
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── accounts/           # TelegramUser, Address, HMAC auth
│   ├── catalog/            # Category, Product, ProductVariant
│   ├── orders/             # Order, OrderItem + signals
│   └── payments/           # Payme (JSON-RPC), Click (MD5) + mock
├── bot/
│   ├── main.py             # Polling / webhook entry point
│   ├── handlers.py         # /start, callback queries
│   ├── keyboards.py        # Reply + inline keyboard builders
│   └── notifications.py   # Customer & admin group messages
├── manage.py
├── requirements.txt
├── Procfile
├── railway.json
└── .env.example
```

---

## Local Setup

```bash
cd backend

# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env
# Edit .env — at minimum set BOT_TOKEN

# 4. Run migrations (uses SQLite locally)
python manage.py migrate

# 5. Create superuser for admin panel
python manage.py createsuperuser

# 6. Start dev server
python manage.py runserver

# 7. Start bot (in a separate terminal)
python -m bot.main
```

Admin panel: http://localhost:8000/admin/

---

## API Endpoints

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| GET | `/api/categories/` | — | Kategoriyalar ro'yxati |
| GET | `/api/products/` | — | Mahsulotlar (`?category=slug&search=&ordering=`) |
| GET | `/api/products/<id>/` | — | Mahsulot detali |
| GET | `/api/profile/` | ✅ | Foydalanuvchi profili |
| GET/POST | `/api/addresses/` | ✅ | Manzillar |
| GET/PATCH/DELETE | `/api/addresses/<id>/` | ✅ | Manzil detali |
| POST | `/api/orders/` | ✅ | Buyurtma yaratish |
| GET | `/api/orders/` | ✅ | Buyurtmalar tarixi |
| GET | `/api/orders/<id>/` | ✅ | Buyurtma detali |
| POST | `/api/payments/payme/checkout/` | ✅ | Payme checkout URL |
| POST | `/api/payments/click/checkout/` | ✅ | Click checkout URL |
| POST | `/api/payments/payme/callback/` | — | Payme webhook |
| POST | `/api/payments/click/callback/` | — | Click webhook |

### Authentication

Barcha `✅` endpointlar uchun header:
```
Authorization: TelegramInitData <url-encoded initData>
```

**Debug bypass** (faqat `DEBUG=True` da):
```
Authorization: TelegramInitData debug
```

---

## Payment Mock Mode

`.env` da `PAYMENTS_MOCK_MODE=True` bo'lsa:
- `/api/payments/payme/checkout/` va `/api/payments/click/checkout/` real checkout URL
  o'rniga darhol `order.payment_status = 'paid'` qilib qo'yadi
- Javob: `{"mock": true, "order_id": 1, "payment_status": "paid"}`

Real kalitlar kelganda faqat `.env` da `PAYMENTS_MOCK_MODE=False` qiling —
Payme/Click kodi o'zgarmaydi.

---

## Railway Deploy

1. Railway'da yangi loyiha yarating
2. PostgreSQL addon qo'shing
3. Environment variables sozlang (`.env.example` ga qarang)
4. `DJANGO_SETTINGS_MODULE=config.settings.production` qo'shing
5. Deploy tugaydi — `railway.json` avtomatik `migrate` va `collectstatic` bajaradi

**Bot uchun alohida Railway service:**
```
Start command: python -m bot.main
```

---

## Bot Commands

- `/start` — Salomlashish + "🛍 Do'konni ochish" WebApp tugmasi
- `📦 Buyurtmalarim` — Mini App ga yo'naltirish

**Admin guruh inline tugmalari:**
- ✅ Tasdiqlash → status: `tayyorlanmoqda`
- 🚴 Yetkazishga chiqarish → status: `yolda`
- ✔️ Yetkazildi → status: `yetkazildi`
- ❌ Bekor qilish → status: `bekor_qilindi`

Har bir status o'zgarishida mijozga avtomatik xabar yuboriladi.
