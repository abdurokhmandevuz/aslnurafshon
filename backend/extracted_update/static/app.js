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
                // Profil sahifasida bo'lsak — darhol yangilaymiz
                if (window.location.pathname.includes('/profile/')) {
                    loadProfile();
                }
            }
        })
        .catch(() => {});
    }
}


// Setup common UI elements on load
document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname.includes('/profile/')) {
        loadProfile();
    }
});

async function loadProductDetail() {
    const urlParams = new URLSearchParams(window.location.search);
    const productId = urlParams.get('id');
    if (!productId) return;

    try {
        const p = await fetchAPI(`/catalog/products/${productId}/`);
        
        // Populate DOM elements (assuming they have IDs)
        const imgEl = document.getElementById('product-image');
        const nameEl = document.getElementById('product-name');
        const descEl = document.getElementById('product-description');
        const priceEl = document.getElementById('product-price');
        const addBtn = document.getElementById('product-add-btn');

        if (imgEl) imgEl.src = p.image;
        if (nameEl) nameEl.textContent = p.name;
        if (descEl) descEl.textContent = p.description || '';
        
        const price = p.variants[0]?.price || 0;
        if (priceEl) priceEl.textContent = `${price.toLocaleString()} UZS`;

        if (addBtn) {
            addBtn.onclick = () => addToCart(p.id, p.name, price, p.image);
        }
    } catch (e) {
        console.error("Product detail error:", e);
    }
}

async function loadHome() {
    const bannersContainer = document.getElementById('home-banners');
    const popularContainer = document.getElementById('home-popular');
    const newContainer = document.getElementById('home-new');

    try {
        const data = await fetchAPI('/catalog/home/');
        
        // If we have DOM elements, populate them
        if (popularContainer && data.popular_products) {
            popularContainer.innerHTML = '';
            data.popular_products.forEach(p => {
                const price = p.min_price ? p.min_price.toLocaleString() : '0';
                popularContainer.innerHTML += `
                <div class="snap-start shrink-0 w-[160px] md:w-[200px] flex flex-col group cursor-pointer" onclick="window.location.href='mahsulot.html?id=${p.id}'">
                    <div class="w-full aspect-square rounded-xl overflow-hidden bg-surface-container-low mb-sm relative">
                        <img src="${p.image}" alt="${p.name}" class="w-full h-full object-cover mix-blend-multiply group-hover:scale-105 transition-transform duration-500">
                    </div>
                    <h4 class="font-label-md text-label-md text-on-surface line-clamp-2">${p.name}</h4>
                    <p class="font-headline-sm text-headline-sm text-primary mt-1">${price} UZS</p>
                </div>`;
            });
        }
        
        if (newContainer && data.new_products) {
            newContainer.innerHTML = '';
            data.new_products.forEach(p => {
                const price = p.min_price ? p.min_price.toLocaleString() : '0';
                newContainer.innerHTML += `
                <div class="snap-start shrink-0 w-[160px] md:w-[200px] flex flex-col group cursor-pointer" onclick="window.location.href='mahsulot.html?id=${p.id}'">
                    <div class="w-full aspect-square rounded-xl overflow-hidden bg-surface-container-low mb-sm relative">
                        <img src="${p.image}" alt="${p.name}" class="w-full h-full object-cover mix-blend-multiply group-hover:scale-105 transition-transform duration-500">
                        <div class="absolute top-2 left-2 bg-secondary text-on-secondary text-[10px] font-bold px-2 py-1 rounded-full">YANGI</div>
                    </div>
                    <h4 class="font-label-md text-label-md text-on-surface line-clamp-2">${p.name}</h4>
                    <p class="font-headline-sm text-headline-sm text-primary mt-1">${price} UZS</p>
                </div>`;
            });
        }
    } catch (e) {
        console.error("Home error:", e);
    }
}

async function loadOrders() {
    const container = document.getElementById('orders-container');
    if (!container) return;

    try {
        const res = await fetchAPI('/orders/');
        const orders = res.results || res;
        container.innerHTML = '';
        if (orders.length === 0) {
            container.innerHTML = '<p class="text-center text-on-surface-variant p-4">Sizda hali buyurtmalar yo`q.</p>';
            return;
        }

        orders.forEach(order => {
            const date = new Date(order.created_at).toLocaleDateString('uz-UZ');
            container.innerHTML += `
            <div class="bg-surface-container-lowest rounded-xl p-md mb-sm border border-surface-container-low shadow-sm">
                <div class="flex justify-between items-center mb-2">
                    <span class="font-label-md font-bold text-on-surface">Buyurtma #${order.id}</span>
                    <span class="font-label-sm text-outline-variant">${date}</span>
                </div>
                <div class="text-on-surface-variant font-body-md text-sm mb-2">
                    Jami: <span class="font-bold text-primary">${order.total_amount.toLocaleString()} UZS</span>
                </div>
                <div class="text-on-surface-variant font-body-md text-sm">
                    Holati: <span class="text-secondary font-bold">${order.status_display || order.status}</span>
                </div>
            </div>`;
        });
    } catch (e) {
        container.innerHTML = '<p class="text-center text-error p-4">Buyurtmalarni yuklashda xatolik.</p>';
    }
}

async function loadCatalog() {
    const grid = document.getElementById('products-grid');
    if (!grid) return;
    
    try {
        const res = await fetchAPI('/catalog/products/');
        const products = res.results || res;
        grid.innerHTML = ''; // Tozalash

        products.forEach(p => {
            const price = parseInt(p.variants[0]?.price || 0).toLocaleString();
            grid.innerHTML += `
            <div class="bg-surface-container-lowest rounded-lg p-sm flex flex-col relative transition-shadow hover:shadow-[0_8px_30px_rgba(74,46,30,0.08)] shadow-[0_4px_20px_rgba(74,46,30,0.04)] border border-outline-variant/20 group">
                <div class="w-full aspect-square rounded-lg overflow-hidden mb-sm bg-surface-container-low relative">
                    <img class="w-full h-full object-cover mix-blend-multiply group-hover:scale-105 transition-transform duration-500" src="${p.image}" alt="${p.name}"/>
                    ${p.is_new ? '<div class="absolute top-2 left-2 bg-secondary text-on-secondary text-[10px] font-bold px-2 py-1 rounded-full uppercase tracking-wider">Yangi</div>' : ''}
                </div>
                <div class="flex-grow flex flex-col justify-between">
                    <div>
                        <h3 class="font-label-md text-label-md text-on-surface line-clamp-2 leading-tight">${p.name}</h3>
                        <p class="font-label-sm text-label-sm text-on-surface-variant mt-1">${p.variants[0]?.weight_label || ''}</p>
                    </div>
                    <div class="mt-md flex justify-between items-end">
                        <span class="font-headline-sm text-headline-sm text-primary">${price} UZS</span>
                    </div>
                </div>
                <button onclick="addToCart(${p.id}, '${p.name}', ${p.variants[0]?.price}, '${p.image}')" aria-label="Savatga qo'shish" class="absolute bottom-sm right-sm w-8 h-8 bg-secondary text-on-secondary rounded-lg flex items-center justify-center shadow-md hover:bg-primary transition-colors active:scale-95">
                    <span class="material-symbols-outlined text-[20px]">add</span>
                </button>
            </div>`;
        });
    } catch (e) {
        grid.innerHTML = '<div class="col-span-full text-center text-error">Mah savatni yuklashda xatolik yuz berdi.</div>';
    }
}

async function addToCart(id, quantity = 1) {
    try {
        const res = await fetch('/api/cart/update/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ variant_id: id, quantity: quantity })
        });
        const data = await res.json();
        if(data.status === 'ok') {
            if (window.Telegram && window.Telegram.WebApp) {
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

function updateCartCount() {
    const cart = getCart();
    const count = cart.reduce((sum, item) => sum + item.quantity, 0);
    // Find cart badge elements and update them
    document.querySelectorAll('.cart-badge').forEach(badge => {
        badge.textContent = count;
        badge.style.display = count > 0 ? 'flex' : 'none';
    });
}

// Sahifa yuklanganda savat sonini yangilash
document.addEventListener('DOMContentLoaded', updateCartCount);

function loadCart() {
    const container = document.getElementById('cart-items-container');
    const totalEl = document.getElementById('cart-total-price');
    const emptyState = document.getElementById('cart-empty-state');
    const cartWrapper = document.getElementById('cart-wrapper');
    if (!container) return;

    const cart = getCart();
    if (cart.length === 0) {
        if(emptyState) emptyState.style.display = 'flex';
        if(cartWrapper) cartWrapper.style.display = 'none';
        return;
    }

    if(emptyState) emptyState.style.display = 'none';
    if(cartWrapper) cartWrapper.style.display = 'block';

    container.innerHTML = '';
    let total = 0;

    cart.forEach((item, index) => {
        const itemTotal = item.price * item.quantity;
        total += itemTotal;
        container.innerHTML += `
        <div class="flex gap-md py-md border-b border-outline-variant/30 last:border-0">
            <img class="w-20 h-20 rounded-lg object-cover bg-surface-container-low" src="${item.image}" alt="${item.name}">
            <div class="flex-grow flex flex-col justify-between">
                <div class="flex justify-between items-start">
                    <h3 class="font-label-md text-label-md text-on-surface line-clamp-2">${item.name}</h3>
                    <button onclick="removeFromCart(${index})" class="text-on-surface-variant hover:text-error transition-colors p-1">
                        <span class="material-symbols-outlined text-[20px]">delete</span>
                    </button>
                </div>
                <div class="flex justify-between items-end mt-2">
                    <span class="font-headline-sm text-headline-sm text-primary">${itemTotal.toLocaleString()} UZS</span>
                    <div class="flex items-center gap-3 bg-surface-container-low rounded-full px-2 py-1">
                        <button onclick="updateQuantity(${index}, -1)" class="w-6 h-6 flex items-center justify-center rounded-full bg-surface text-on-surface hover:bg-surface-dim transition-colors shadow-sm">
                            <span class="material-symbols-outlined text-[16px]">remove</span>
                        </button>
                        <span class="font-label-md text-label-md w-4 text-center">${item.quantity}</span>
                        <button onclick="updateQuantity(${index}, 1)" class="w-6 h-6 flex items-center justify-center rounded-full bg-secondary text-on-secondary hover:bg-primary transition-colors shadow-sm">
                            <span class="material-symbols-outlined text-[16px]">add</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>`;
    });

    if (totalEl) totalEl.textContent = `${total.toLocaleString()} UZS`;
}

function updateQuantity(index, change) {
    const cart = getCart();
    cart[index].quantity += change;
    if (cart[index].quantity <= 0) {
        cart.splice(index, 1);
    }
    saveCart(cart);
    loadCart();
}

function removeFromCart(index) {
    const cart = getCart();
    cart.splice(index, 1);
    saveCart(cart);
    loadCart();
}

async function loadCheckout() {
    const container = document.getElementById('checkout-items');
    const subtotalEl = document.getElementById('checkout-subtotal');
    const totalEl = document.getElementById('checkout-total');
    if (!container) return;

    const cart = getCart();
    if (cart.length === 0) {
        window.location.href = 'katalog.html';
        return;
    }

    container.innerHTML = '';
    let total = 0;
    const deliveryFee = 15000;

    cart.forEach(item => {
        const itemTotal = item.price * item.quantity;
        total += itemTotal;
        container.innerHTML += `
        <div class="flex items-center gap-4 border-b border-surface-container-high pb-4">
            <div class="w-16 h-16 rounded-lg bg-surface-container-low overflow-hidden flex-shrink-0">
                <img class="w-full h-full object-cover" src="${item.image}" alt="${item.name}">
            </div>
            <div class="flex-1">
                <h4 class="font-label-md text-label-md text-on-surface">${item.name}</h4>
                <div class="flex justify-between items-center mt-2">
                    <span class="font-headline-sm text-headline-sm text-primary">${itemTotal.toLocaleString()} UZS</span>
                    <span class="font-label-md text-label-md text-on-surface-variant bg-surface-container px-2 py-1 rounded">x ${item.quantity}</span>
                </div>
            </div>
        </div>`;
    });

    if (subtotalEl) subtotalEl.textContent = `${total.toLocaleString()} UZS`;
    if (totalEl) totalEl.textContent = `${(total + deliveryFee).toLocaleString()} UZS`;

    // Fetch phone number
    try {
        const profile = await fetchAPI('/accounts/profile/');
        const phoneInput = document.getElementById('checkout-phone');
        if (phoneInput && profile.phone) {
            phoneInput.value = profile.phone;
        }
    } catch (e) {
        console.error("Profilni yuklashda xatolik", e);
    }
}

async function submitOrder() {
    const cart = getCart();
    if (cart.length === 0) return;

    const items = cart.map(item => ({ product_variant_id: item.id, quantity: item.quantity }));
    // Hozircha "address" qismi inputdan olinadi, soddalashtirilgan:
    const addressInput = document.querySelector('input[placeholder="Manzilni kiriting yoki xaritadan tanlang"]');
    const address = addressInput ? addressInput.value : 'Toshkent shahar';
    
    const phoneInput = document.getElementById('checkout-phone');
    const phoneError = document.getElementById('checkout-phone-error');
    if (phoneInput && !phoneInput.value.trim()) {
        if (phoneError) phoneError.classList.remove('hidden');
        return;
    }
    if (phoneError) phoneError.classList.add('hidden');
    
    // Save phone to profile if it exists
    if (phoneInput && phoneInput.value.trim()) {
        try {
            await fetchAPI('/accounts/profile/', {
                method: 'PATCH',
                body: JSON.stringify({ phone: phoneInput.value.trim() })
            });
        } catch (e) {
            console.error("Telefon raqamni saqlashda xato", e);
        }
    }

    try {
        const response = await fetchAPI('/orders/', {
            method: 'POST',
            body: JSON.stringify({ items, address })
        });
        
        // Agar to'lov muvaffaqiyatli bo'lsa (yoki Payme linki kelsa)
        localStorage.removeItem('cart');
        
        if (response.payment_url) {
            if (window.Telegram && window.Telegram.WebApp) {
                window.Telegram.WebApp.openLink(response.payment_url);
            } else {
                window.location.href = response.payment_url;
            }
        } else {
            window.location.href = 'tasdiqlandi.html';
        }
    } catch (e) {
        alert("Buyurtmani yuborishda xatolik yuz berdi. Iltimos qayta urinib ko'ring.");
    }
}

// Xavfsiz Fetch funksiyasi (Avtomatik Telegram malumotlarini jo'natadi)
async function fetchAPI(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    
    const headers = {
        'Content-Type': 'application/json',
        'Telegram-Data': initData // Backend dagi TelegramInitDataAuthentication uchun
    };

    if (options.headers) {
        Object.assign(headers, options.headers);
    }

    const response = await fetch(url, { ...options, headers });
    if (!response.ok) {
        console.error('API Error:', await response.text());
        throw new Error('Tarmoq xatosi yoki ruxsat yo`q');
    }
    return response.json();
}

// Profil sahifasini yuklash
function loadProfile() {
    // Yangi IDlar (profil.html da ishlatilgan)
    const nameEl = document.getElementById('tg-profile-name');
    const phoneEl = document.getElementById('tg-profile-phone');
    const imgEl = document.getElementById('tg-profile-photo');
    const initialEl = document.getElementById('tg-profile-initial');

    if (!nameEl) return; // Profil sahifasida emasmiz

    if (tgUser && (tgUser.first_name || tgUser.username)) {
        // Ism
        const fullName = [tgUser.first_name, tgUser.last_name].filter(Boolean).join(' ');
        if (nameEl && fullName) nameEl.textContent = fullName;

        // Boshlang'ich harf
        const initial = (tgUser.first_name || tgUser.username || '?')[0].toUpperCase();
        if (initialEl) initialEl.textContent = initial;

        // Rasm
        if (imgEl && tgUser.photo_url) {
            imgEl.src = tgUser.photo_url;
            imgEl.classList.remove('hidden');
            if (initialEl) initialEl.classList.add('hidden');
        }

        // Telefon yoki username
        if (phoneEl) {
            const currentPhone = phoneEl.textContent.trim();
            if (currentPhone === 'Telefon raqam kiritilmagan' && tgUser.username) {
                phoneEl.textContent = '@' + tgUser.username;
            }
        }
    } else {
        // Hech qanday ma'lumot yo'q — oddiy holatni ko'rsatamiz
        if (nameEl && nameEl.textContent.trim() === 'Yuklanmoqda...') {
            nameEl.textContent = 'Foydalanuvchi';
        }
        if (initialEl) initialEl.textContent = '?';
    }
}
