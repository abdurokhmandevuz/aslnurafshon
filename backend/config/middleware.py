class NoCacheMiddleware:
    """
    Ensures that HTML pages (like SSR templates) are never cached by clients, 
    especially aggressive Telegram WebApp clients.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # We only want to prevent caching for HTML responses (our SSR pages).
        # Static files (CSS, JS, Images) are served by WhiteNoise and can be cached.
        if "text/html" in response.get("Content-Type", ""):
            response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"
            
        return response


from django.shortcuts import redirect
from apps.accounts.models import Courier

class CourierRedirectMiddleware:
    """
    If a logged-in user is registered as an active courier,
    and they try to visit the customer-facing storefront (catalog, cart, profile, etc.),
    redirect them to the courier panel.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user and request.user.is_authenticated:
            telegram_id = getattr(request.user, 'telegram_id', None)
            if telegram_id:
                is_courier = Courier.objects.filter(telegram_id=telegram_id, is_active=True).exists()
                if is_courier:
                    path = request.path
                    if not path.startswith('/courier') and not path.startswith('/admin') and not path.startswith('/auth') and path != '/':
                        return redirect('/courier/')
                else:
                    # Regular customer trying to access courier pages
                    if request.path.startswith('/courier/'):
                        return redirect('/catalog/')
            else:
                # Standard Django User (e.g. Admin) trying to access courier pages
                if request.path.startswith('/courier/'):
                    return redirect('/catalog/')
        else:
            if request.path.startswith('/courier/'):
                return redirect('/')
                
        return self.get_response(request)


from django.core.cache import cache
from django.http import HttpResponseForbidden

class RateLimitMiddleware:
    """
    Lightweight rate limiting middleware using Django cache.
    Limits each IP to 100 requests per minute.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin/') or request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)

        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        cache_key = f"rl_{ip}"
        requests_count = cache.get(cache_key, 0)

        if requests_count >= 100:
            return HttpResponseForbidden("Too many requests. Please try again in a minute.")

        cache.set(cache_key, requests_count + 1, timeout=60)
        return self.get_response(request)
