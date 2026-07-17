// Asl Nurafshon - Frontend App Script
const API_BASE_URL = 'https://aslnurafshon.duckdns.org/api';

// Telegram Web App Initialization
let tg = window.Telegram ? window.Telegram.WebApp : null;
let tgUser = null;
let initData = '';

if (tg) {
    tg.ready();
    tg.expand();
    initData = tg.initData || '';
    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
        tgUser = tg.initDataUnsafe.user;
        localStorage.setItem('tg_user', JSON.stringify({
            first_name: tgUser.first_name || '',
            last_name: tgUser.last_name || '',
            username: tgUser.username || '',
            photo_url: tgUser.photo_url || '',
            id: tgUser.id || 0
        }));
    } else {
        // initDataUnsafe bo'sh — localStorage dan olamiz
        try {
            const stored = localStorage.getItem('tg_user');
            if (stored) tgUser = JSON.parse(stored);
        } catch(e) {}
    }

    // initData mavjud bo'lsa — fonda serverdan user ma'lumotlarini olamiz
    // Bu har qanday sahifada ishlaydi (session o'tkazib yuborilsa ham)
    if (initData && (!tgUser || !tgUser.full_name)) {
        fetch('/auth/telegram/', {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ initData: initData })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'ok' && data.user) {
                const u = data.user;
                // Serverdan kelgan ishonchli ma'lumotlarni saqlaymiz
                const prev = {};
                try { Object.assign(prev, JSON.parse(localStorage.getItem('tg_user') || '{}')); } catch(e){}
                const saved = {
                    full_name: u.full_name || prev.full_name || '',
                    first_name: (u.full_name || '').split(' ')[0] || prev.first_name || '',
                    last_name: (u.full_name || '').split(' ').slice(1).join(' ') || prev.last_name || '',
                    username: u.username || prev.username || '',
                    phone: u.phone || prev.phone || '',
                    photo_url: prev.photo_url || '',
                    id: u.telegram_id || prev.id || 0
                };
                localStorage.setItem('tg_user', JSON.stringify(saved));
                tgUser = saved;
            }
        })
        .catch(() => {});
    }
}

// Global Savatni saqlash yordamchi funksiyalari (Faqat xavfsizlik uchun, asosiy savat Session da)
function getCart() {
    try {
        const cart = localStorage.getItem('cart');
        return cart ? JSON.parse(cart) : [];
    } catch (e) {
        return [];
    }
}

function saveCart(cart) {
    localStorage.setItem('cart', JSON.stringify(cart));
}

async function addToCart(id, quantity = 1) {
    try {
        const res = await fetch('/cart/update/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken') || ''
            },
            body: JSON.stringify({
                variant_id: id,
                quantity: quantity
            })
        });
        
        if (res.ok) {
            const data = await res.json();
            // Agar WebApp bo'lsa haptic feedback berish
            if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.HapticFeedback) {
                window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
            }
            // Update cart count visually if there's an element
            const countEls = document.querySelectorAll('.cart-count-badge');
            countEls.forEach(el => {
                el.textContent = data.cart_count;
                if(data.cart_count > 0) {
                    el.classList.remove('hidden');
                } else {
                    el.classList.add('hidden');
                }
            });
            // If we are on the cart page, reload it to reflect changes
            if(window.location.pathname.includes('/cart/')) {
                window.location.reload();
            }
        }
    } catch(e) {
        console.error("Cart error:", e);
    }
}

// CSRF tokenni cookie'dan olish
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `fixed top-4 left-1/2 -translate-x-1/2 z-[9999] px-6 py-3 rounded-full text-white font-label-md shadow-lg transition-all duration-300 transform translate-y-[-20px] opacity-0 flex items-center gap-2 ${
        type === 'error' ? 'bg-error shadow-error/20' : 'bg-secondary shadow-secondary/20'
    }`;
    
    const icon = document.createElement('span');
    icon.className = 'material-symbols-outlined text-[18px]';
    icon.textContent = type === 'error' ? 'error' : 'check_circle';
    
    const text = document.createElement('span');
    text.textContent = message;
    
    toast.appendChild(icon);
    toast.appendChild(text);
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.transform = 'translate(-50%, 0)';
        toast.style.opacity = '1';
    }, 10);
    
    setTimeout(() => {
        toast.style.transform = 'translate(-50%, -20px)';
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

async function addBundleToCart(id, quantity = 1) {
    try {
        const res = await fetch('/cart/update/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken') || ''
            },
            body: JSON.stringify({
                bundle_id: id,
                quantity: quantity
            })
        });
        
        if (res.ok) {
            const data = await res.json();
            if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.HapticFeedback) {
                window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
            }
            const countEls = document.querySelectorAll('.cart-count-badge');
            countEls.forEach(el => {
                el.textContent = data.cart_count;
                if(data.cart_count > 0) {
                    el.classList.remove('hidden');
                } else {
                    el.classList.add('hidden');
                }
            });
            if(window.location.pathname.includes('/cart/')) {
                window.location.reload();
            } else {
                showToast("To'plam savatga qo'shildi!", 'success');
            }
        }
    } catch(e) {
        console.error("Cart error:", e);
    }
}
