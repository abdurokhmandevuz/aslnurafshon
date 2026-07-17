import json
from django.contrib.auth import login
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from .authentication import TelegramInitDataAuthentication
from django.conf import settings


@csrf_exempt
def auth_telegram_view(request):
    """Splash screen'dan chaqiriladi — initData tekshirib, session o'rnatadi."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            init_data = data.get('initData', '')

            auth = TelegramInitDataAuthentication()
            if settings.DEBUG and init_data == 'debug':
                user, _ = auth._get_or_create_user({
                    'id': 0, 'first_name': 'Debug', 'username': 'debug'
                })
            else:
                user_data = auth._validate_and_parse(init_data)
                user = auth._get_or_create_user(user_data)

            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            request.session.modified = True

            # User ma'lumotlarini ham qaytaramiz — JS localStorage ga saqlaydi
            response = JsonResponse({
                'status': 'ok',
                'user': {
                    'full_name': user.full_name or '',
                    'username': user.username or '',
                    'phone': getattr(user, 'phone', '') or '',
                    'telegram_id': user.telegram_id,
                }
            })
            return response
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'invalid method'}, status=405)


def splash_screen_view(request):
    """Boshlang'ich yuklanish ekrani — JS orqali auth qiladi."""
    # Session bo'lsa ham splash screen'ni ko'rsatamiz
    # chunki JS localStorage ni to'ldirishi kerak
    return render(request, 'index.html')


def profile_view(request):
    """
    Profil sahifasi.
    Foydalanuvchi ma'lumotlarini initData orqali DB dan olamiz.
    Session ishlamasa ham ishlaydi.
    """
    from apps.orders.models import Order

    user = None
    user_data = {
        'full_name': '',
        'username': '',
        'phone': '',
        'photo_url': '',
        'initial': '?',
    }
    orders_count = 0

    # 1. Session orqali tekshiramiz
    if request.user.is_authenticated:
        user = request.user

    # 2. Agar session yo'q bo'lsa, initData'dan olamiz (query param yoki header)
    if not user:
        init_data = (
            request.GET.get('initData') or
            request.POST.get('initData') or
            request.headers.get('X-Telegram-Init-Data', '')
        )
        if init_data:
            try:
                auth = TelegramInitDataAuthentication()
                user_info = auth._validate_and_parse(init_data)
                user = auth._get_or_create_user(user_info)
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            except Exception:
                pass

    # 3. User topilsa, ma'lumotlarni oldb uzatamiz
    if user:
        name = user.full_name or user.username or ''
        user_data = {
            'full_name': name,
            'username': user.username or '',
            'phone': getattr(user, 'phone', '') or '',
            'photo_url': '',  # Bot orqali olsa bo'ladi (kelajakda)
            'initial': name[0].upper() if name else '?',
        }
        orders_count = Order.objects.filter(user=user).count()

    return render(request, 'profil.html', {
        'user_data': user_data,
        'orders_count': orders_count,
    })
