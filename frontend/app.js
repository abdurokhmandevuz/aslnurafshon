// ═══════════════════════════════════════════════════════════════
// Asl Nurafshon — Frontend App Script
// ═══════════════════════════════════════════════════════════════

const API_BASE_URL = '/api';

// ─── Telegram Web App ─────────────────────────────────────────
let tg = window.Telegram ? window.Telegram.WebApp : null;
let tgUser = null;
let initData = '';

if (tg) {
    tg.ready();
    tg.expand();
    initData = tg.initData || '';
    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
        tgUser = tg.initDataUnsafe.user;
    }
    // Telegram theme ranglarini qo'llash
    applyTelegramTheme();
}

function applyTelegramTheme() {
    if (!tg) return;
    const isDark = tg.colorScheme === 'dark';
    document.documentElement.classList.toggle('dark', isDark);
    // Telegram header rangini o'rnatish
    if (tg.setHeaderColor) {
        tg.setHeaderColor(isDark ? '#1a1a1a' : '#ffffff');
    }
    if (tg.setBackgroundColor) {
        tg.setBackgroundColor(isDark ? '#1a1a1a' : '#f9f9f9');
    }
}

// ─── Toast xabarlar ──────────────────────────────────────────
let toastTimeout = null;

function showToast(message, type = 'success', duration = 3000) {
    let toast = document.getElementById('toast-notification');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast-notification';
        toast.style.cssText = `
            position: fixed; bottom: 90px; left: 50%; transform: translateX(-50%) translateY(20px);
            padding: 12px 20px; border-radius: 12px; font-size: 14px; font-weight: 600;
            z-index: 9999; opacity: 0; transition: all 0.3s ease; white-space: nowrap;
            box-shadow: 0 8px 30px rgba(0,0,0,0.15); max-width: 90vw;
        `;
        document.body.appendChild(toast);
    }

    const colors = {
        success: { bg: '#4CAF50', text: '#fff' },
        error: { bg: '#F44336', text: '#fff' },
        info: { bg: '#32190b', text: '#fff' },
        warning: { bg: '#FF9800', text: '#fff' },
    };

    const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
    const c = colors[type] || colors.info;

    toast.style.background = c.bg;
    toast.style.color = c.text;
    toast.textContent = `${icons[type] || ''} ${message}`;

    requestAnimationFrame(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateX(-50%) translateY(0)';
    });

    if (toastTimeout) clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(-50%) translateY(20px)';
    }, duration);
}

// ─── Haptic Feedback ─────────────────────────────────────────
function haptic(type = 'light') {
    if (tg && tg.HapticFeedback) {
        if (type === 'success') tg.HapticFeedback.notificationOccurred('success');
        else if (type === 'error') tg.HapticFeedback.notificationOccurred('error');
        else if (type === 'warning') tg.HapticFeedback.notificationOccurred('warning');
        else tg.HapticFeedback.impactOccurred(type);
    }
}

// ─── Skeleton Loading ─────────────────────────────────────────
function skeletonCard() {
    return `
    <div class="skeleton-card rounded-xl overflow-hidden bg-surface-container-low animate-pulse">
        <div class="aspect-square bg-surface-container-high"></div>
        <div class="p-3">
            <div class="h-4 bg-surface-container-high rounded mb-2 w-3/4"></div>
            <div class="h-4 bg-surface-container-high rounded w-1/2"></div>
        </div>
    </div>`;
}

function showSkeletons(containerId, count = 4) {
    const el = document.getElementById(containerId);
    if (el) el.innerHTML = Array(count).fill(skeletonCard()).join('');
}

// ─── DOMContentLoaded ─────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    updateCartCount();

    const path = window.location.pathname;

    if (path.includes('profil.html')) loadProfile();
    if (path.includes('katalog.html')) loadCatalog();
    if (path.includes('savat.html')) loadCart();
    if (path.includes('checkout.html')) loadCheckout();
    if (path.includes('index.html') || path.endsWith('/') || path === '') loadHome();
    if (path.includes('buyurtmalar.html')) loadOrders();
    if (path.includes('mahsulot.html')) loadProductDetail();
    if (path.includes('aksiyalar.html')) loadPromos();
});

// ─── Profil ───────────────────────────────────────────────────
function loadProfile() {
    if (!tgUser) return;
    const nameEl = document.querySelector('.profile-name');
    const userEl = document.querySelector('.profile-username');
    const imgEl = document.querySelector('.profile-image');
    if (nameEl) nameEl.textContent = `${tgUser.first_name} ${tgUser.last_name || ''}`.trim();
    if (userEl && tgUser.username) userEl.textContent = `@${tgUser.username}`;
    if (imgEl && tgUser.photo_url) imgEl.src = tgUser.photo_url;
}

// ─── Home ─────────────────────────────────────────────────────
async function loadHome() {
    showSkeletons('home-popular', 4);
    showSkeletons('home-new', 4);

    try {
        const data = await fetchAPI('/catalog/home/');

        // Banner slider
        const bannersEl = document.getElementById('home-banners');
        if (bannersEl && data.banners && data.banners.length > 0) {
            bannersEl.innerHTML = `
            <div class="banner-slider relative overflow-hidden rounded-2xl" id="banner-slider">
                <div class="banner-track flex transition-transform duration-500 ease-in-out" id="banner-track">
                    ${data.banners.map(b => `
                    <div class="banner-slide flex-shrink-0 w-full relative cursor-pointer"
                         onclick="${b.link_url ? `window.location.href='${b.link_url}'` : ''}">
                        <img src="${b.image}" alt="${b.title}"
                             class="w-full h-44 object-cover">
                        <div class="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent flex flex-col justify-end p-4">
                            <h3 class="text-white font-bold text-lg">${b.title || ''}</h3>
                            ${b.button_text ? `<span class="mt-1 inline-block text-white/80 text-sm">${b.button_text} →</span>` : ''}
                        </div>
                    </div>`).join('')}
                </div>
                ${data.banners.length > 1 ? `
                <div class="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-1.5" id="banner-dots">
                    ${data.banners.map((_, i) => `<div class="dot w-2 h-2 rounded-full ${i === 0 ? 'bg-white' : 'bg-white/40'} transition-all cursor-pointer" onclick="goToSlide(${i})"></div>`).join('')}
                </div>` : ''}
            </div>`;
            if (data.banners.length > 1) initBannerSlider(data.banners.length);
        }

        // Mashhur mahsulotlar
        const popularEl = document.getElementById('home-popular');
        if (popularEl && data.popular_products) {
            popularEl.innerHTML = data.popular_products.map(p => productCard(p)).join('');
        }

        // Yangi kelganlar
        const newEl = document.getElementById('home-new');
        if (newEl && data.new_products) {
            newEl.innerHTML = data.new_products.map(p => productCardHorizontal(p, 'YANGI')).join('');
        }

        // Chegirmadagi mahsulotlar
        const saleEl = document.getElementById('home-sale');
        if (saleEl && data.sale_products && data.sale_products.length > 0) {
            saleEl.innerHTML = data.sale_products.map(p => productCardHorizontal(p, '🔥')).join('');
        }

    } catch (e) {
        console.error('Home error:', e);
        showToast("Ma'lumotlarni yuklashda xatolik", 'error');
    }
}

// ─── Banner Slider ────────────────────────────────────────────
let currentSlide = 0;
let sliderInterval = null;
let totalSlides = 0;

function initBannerSlider(count) {
    totalSlides = count;
    sliderInterval = setInterval(() => {
        currentSlide = (currentSlide + 1) % totalSlides;
        updateSlider();
    }, 4000);
}

function goToSlide(index) {
    currentSlide = index;
    updateSlider();
    if (sliderInterval) { clearInterval(sliderInterval); initBannerSlider(totalSlides); }
}

function updateSlider() {
    const track = document.getElementById('banner-track');
    const dots = document.querySelectorAll('#banner-dots .dot');
    if (track) track.style.transform = `translateX(-${currentSlide * 100}%)`;
    dots.forEach((d, i) => {
        d.classList.toggle('bg-white', i === currentSlide);
        d.classList.toggle('w-4', i === currentSlide);
        d.classList.toggle('bg-white/40', i !== currentSlide);
        d.classList.toggle('w-2', i !== currentSlide);
    });
}

// ─── Product Cards ────────────────────────────────────────────
function productCard(p) {
    const price = p.min_price ? Number(p.min_price).toLocaleString() : '0';
    const oldPrice = p.old_price ? `<span class="text-xs text-outline line-through ml-1">${Number(p.old_price).toLocaleString()}</span>` : '';
    const badge = p.discount_percent ? `<div class="absolute top-2 left-2 bg-error text-white text-[10px] font-bold px-2 py-0.5 rounded-full">-${p.discount_percent}%</div>` : (p.is_new ? `<div class="absolute top-2 left-2 bg-secondary text-on-secondary text-[10px] font-bold px-2 py-0.5 rounded-full">YANGI</div>` : '');

    return `
    <div class="bg-surface-container-lowest rounded-xl overflow-hidden border border-outline-variant/20 shadow-sm hover:shadow-md transition-all group cursor-pointer relative"
         onclick="window.location.href='mahsulot.html?id=${p.id}'">
        <div class="relative aspect-square overflow-hidden bg-surface-container-low">
            <img src="${p.image || 'placeholder.jpg'}" alt="${p.name}"
                 class="w-full h-full object-cover mix-blend-multiply group-hover:scale-105 transition-transform duration-500"
                 onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><rect fill=%22%23eee%22 width=%22100%22 height=%22100%22/></svg>'">
            ${badge}
            <button onclick="event.stopPropagation(); addToCart(${p.id}, '${p.name.replace(/'/g,"\\'")}', ${p.min_price || 0}, '${p.image || ''}')"
                    class="absolute bottom-2 right-2 w-9 h-9 bg-secondary text-on-secondary rounded-xl flex items-center justify-center shadow-lg hover:bg-primary active:scale-95 transition-all opacity-0 group-hover:opacity-100">
                <span class="material-symbols-outlined text-[20px]">add</span>
            </button>
        </div>
        <div class="p-3">
            <h3 class="font-label-md text-label-md text-on-surface line-clamp-2 leading-tight">${p.name}</h3>
            <div class="flex items-center mt-2">
                <span class="font-bold text-primary text-base">${price} UZS</span>
                ${oldPrice}
            </div>
        </div>
    </div>`;
}

function productCardHorizontal(p, badgeText) {
    const price = p.min_price ? Number(p.min_price).toLocaleString() : '0';
    return `
    <div class="snap-start shrink-0 w-[160px] flex flex-col group cursor-pointer"
         onclick="window.location.href='mahsulot.html?id=${p.id}'">
        <div class="w-full aspect-square rounded-xl overflow-hidden bg-surface-container-low mb-2 relative">
            <img src="${p.image || ''}" alt="${p.name}"
                 class="w-full h-full object-cover mix-blend-multiply group-hover:scale-105 transition-transform duration-500">
            <div class="absolute top-2 left-2 bg-secondary text-on-secondary text-[10px] font-bold px-2 py-0.5 rounded-full">${badgeText}</div>
        </div>
        <h4 class="font-label-md text-label-md text-on-surface line-clamp-2 text-sm">${p.name}</h4>
        <p class="font-bold text-primary text-sm mt-1">${price} UZS</p>
    </div>`;
}

// ─── Mahsulot Detail ──────────────────────────────────────────
async function loadProductDetail() {
    const urlParams = new URLSearchParams(window.location.search);
    const productId = urlParams.get('id');
    if (!productId) return;

    try {
        const p = await fetchAPI(`/catalog/products/${productId}/`);

        const imgEl = document.getElementById('product-image');
        const nameEl = document.getElementById('product-name');
        const descEl = document.getElementById('product-description');
        const priceEl = document.getElementById('product-price');
        const addBtn = document.getElementById('product-add-btn');
        const variantsEl = document.getElementById('product-variants');

        if (imgEl) imgEl.src = p.image;
        if (nameEl) nameEl.textContent = p.name;
        if (descEl) descEl.textContent = p.description || '';

        let selectedVariant = p.variants[0];

        // Variantlar
        if (variantsEl && p.variants.length > 1) {
            variantsEl.innerHTML = p.variants.map((v, i) => `
            <button onclick="selectVariant(this, ${v.price}, ${v.id})"
                    class="variant-btn px-4 py-2 rounded-full border text-sm font-semibold transition-all
                           ${i === 0 ? 'bg-primary text-white border-primary' : 'border-outline-variant text-on-surface hover:border-primary'}">
                ${v.weight_label || v.variant_type}
            </button>`).join('');
        }

        if (priceEl) priceEl.textContent = `${Number(selectedVariant?.price || 0).toLocaleString()} UZS`;

        if (addBtn) {
            addBtn.onclick = () => {
                haptic('medium');
                addToCart(selectedVariant?.id || p.id, p.name, selectedVariant?.price || 0, p.image);
                showToast(`${p.name} savatga qo'shildi`, 'success');
            };
        }

        // Sevimlilar
        const favBtn = document.getElementById('favorite-btn');
        if (favBtn) {
            const favs = JSON.parse(localStorage.getItem('favorites') || '[]');
            const isFav = favs.includes(p.id);
            updateFavBtn(favBtn, isFav);
            favBtn.onclick = () => toggleFavorite(p.id, favBtn);
        }

        // O'xshash mahsulotlar
        loadSimilarProducts(p.category_id || p.category, productId);

    } catch (e) {
        console.error('Product detail error:', e);
        showToast("Mahsulot ma'lumotlarini yuklashda xatolik", 'error');
    }
}

function selectVariant(btn, price, variantId) {
    document.querySelectorAll('.variant-btn').forEach(b => {
        b.classList.remove('bg-primary', 'text-white', 'border-primary');
        b.classList.add('border-outline-variant', 'text-on-surface');
    });
    btn.classList.add('bg-primary', 'text-white', 'border-primary');
    btn.classList.remove('border-outline-variant', 'text-on-surface');

    const priceEl = document.getElementById('product-price');
    if (priceEl) priceEl.textContent = `${Number(price).toLocaleString()} UZS`;

    haptic('light');
}

async function loadSimilarProducts(categoryId, currentId) {
    const el = document.getElementById('similar-products');
    if (!el || !categoryId) return;
    try {
        const products = await fetchAPI(`/catalog/products/?category=${categoryId}`);
        const filtered = products.filter(p => p.id != currentId).slice(0, 6);
        if (filtered.length === 0) { el.closest('section')?.remove(); return; }
        el.innerHTML = filtered.map(p => productCardHorizontal(p, '')).join('');
    } catch (e) { /* silent */ }
}

function toggleFavorite(productId, btn) {
    let favs = JSON.parse(localStorage.getItem('favorites') || '[]');
    const isFav = favs.includes(productId);
    if (isFav) {
        favs = favs.filter(id => id !== productId);
        showToast("Sevimlilardan olib tashlandi", 'info');
    } else {
        favs.push(productId);
        showToast("Sevimlilarga qo'shildi ❤️", 'success');
        haptic('medium');
    }
    localStorage.setItem('favorites', JSON.stringify(favs));
    updateFavBtn(btn, !isFav);
}

function updateFavBtn(btn, isFav) {
    btn.innerHTML = `<span class="material-symbols-outlined" style="font-variation-settings:'FILL' ${isFav ? 1 : 0}">${isFav ? 'favorite' : 'favorite'}</span>`;
    btn.classList.toggle('text-error', isFav);
    btn.classList.toggle('text-on-surface-variant', !isFav);
}

// ─── Katalog ──────────────────────────────────────────────────
async function loadCatalog() {
    const grid = document.getElementById('products-grid');
    if (!grid) return;
    showSkeletons('products-grid', 6);

    try {
        const products = await fetchAPI('/catalog/products/');
        if (products.length === 0) {
            grid.innerHTML = '<div class="col-span-full text-center py-12 text-on-surface-variant">Mahsulotlar topilmadi</div>';
            return;
        }
        grid.innerHTML = products.map(p => productCard(p)).join('');
    } catch (e) {
        grid.innerHTML = '<div class="col-span-full text-center text-error py-8">Yuklashda xatolik</div>';
    }
}

// ─── Aksiyalar ────────────────────────────────────────────────
async function loadPromos() {
    const el = document.getElementById('promos-container');
    if (!el) return;
    try {
        const data = await fetchAPI('/catalog/promotions/');
        if (!data || data.length === 0) return;
        el.innerHTML = data.map(promo => `
        <div class="bg-surface-container-lowest rounded-2xl overflow-hidden border border-outline-variant/20 shadow-sm mb-4">
            ${promo.image ? `<img src="${promo.image}" class="w-full h-44 object-cover" alt="${promo.title}">` : ''}
            <div class="p-4">
                <h3 class="font-bold text-on-surface text-lg">${promo.title}</h3>
                ${promo.description ? `<p class="text-on-surface-variant text-sm mt-2">${promo.description}</p>` : ''}
                ${promo.discount_percent ? `<div class="mt-3 inline-block bg-error/10 text-error font-bold px-3 py-1 rounded-full text-sm">-${promo.discount_percent}% chegirma</div>` : ''}
            </div>
        </div>`).join('');
    } catch (e) { /* silent */ }
}

// ─── Savat (Cart) ─────────────────────────────────────────────
function getCart() {
    return JSON.parse(localStorage.getItem('cart')) || [];
}

function saveCart(cart) {
    localStorage.setItem('cart', JSON.stringify(cart));
    updateCartCount();
}

function addToCart(id, name, price, image) {
    const cart = getCart();
    const existing = cart.find(item => item.id === id);
    if (existing) {
        existing.quantity += 1;
    } else {
        cart.push({ id, name, price: Number(price), image, quantity: 1 });
    }
    saveCart(cart);
    haptic('light');
}

function updateCartCount() {
    const cart = getCart();
    const count = cart.reduce((sum, item) => sum + item.quantity, 0);
    document.querySelectorAll('.cart-badge').forEach(badge => {
        badge.textContent = count;
        badge.style.display = count > 0 ? 'flex' : 'none';
    });
}

function loadCart() {
    const container = document.getElementById('cart-items-container');
    const totalEl = document.getElementById('cart-total-price');
    const emptyState = document.getElementById('cart-empty-state');
    const cartWrapper = document.getElementById('cart-wrapper');
    const promoRow = document.getElementById('promo-row');
    if (!container) return;

    const cart = getCart();

    if (cart.length === 0) {
        if (emptyState) emptyState.style.display = 'flex';
        if (cartWrapper) cartWrapper.style.display = 'none';
        return;
    }

    if (emptyState) emptyState.style.display = 'none';
    if (cartWrapper) cartWrapper.style.display = 'block';

    container.innerHTML = '';
    let subtotal = 0;

    cart.forEach((item, index) => {
        const itemTotal = item.price * item.quantity;
        subtotal += itemTotal;
        container.innerHTML += `
        <div class="flex gap-md py-md border-b border-outline-variant/30 last:border-0">
            <img class="w-20 h-20 rounded-xl object-cover bg-surface-container-low flex-shrink-0"
                 src="${item.image}" alt="${item.name}"
                 onerror="this.style.background='#eee'">
            <div class="flex-grow flex flex-col justify-between">
                <div class="flex justify-between items-start">
                    <h3 class="font-label-md text-label-md text-on-surface line-clamp-2 flex-1 mr-2">${item.name}</h3>
                    <button onclick="removeFromCart(${index})" class="text-on-surface-variant hover:text-error transition-colors p-1 flex-shrink-0">
                        <span class="material-symbols-outlined text-[20px]">delete</span>
                    </button>
                </div>
                <div class="flex justify-between items-end mt-2">
                    <span class="font-bold text-primary text-base">${Number(itemTotal).toLocaleString()} UZS</span>
                    <div class="flex items-center gap-2 bg-surface-container-low rounded-full px-2 py-1">
                        <button onclick="updateQuantity(${index}, -1)" class="w-7 h-7 flex items-center justify-center rounded-full bg-surface text-on-surface hover:bg-surface-dim transition-colors">
                            <span class="material-symbols-outlined text-[16px]">remove</span>
                        </button>
                        <span class="font-label-md text-label-md w-5 text-center">${item.quantity}</span>
                        <button onclick="updateQuantity(${index}, 1)" class="w-7 h-7 flex items-center justify-center rounded-full bg-secondary text-on-secondary hover:bg-primary transition-colors">
                            <span class="material-symbols-outlined text-[16px]">add</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>`;
    });

    // Yetkazib berish narxi
    const deliveryFee = subtotal >= 150000 ? 0 : 15000;
    const total = subtotal + deliveryFee;

    const subtotalEl = document.getElementById('cart-subtotal');
    const deliveryEl = document.getElementById('cart-delivery');
    const discountEl = document.getElementById('cart-discount');

    if (subtotalEl) subtotalEl.textContent = `${Number(subtotal).toLocaleString()} UZS`;
    if (deliveryEl) deliveryEl.textContent = deliveryFee === 0 ? 'Bepul 🎉' : `${Number(deliveryFee).toLocaleString()} UZS`;
    if (totalEl) totalEl.textContent = `${Number(total).toLocaleString()} UZS`;

    // Minimal summa xabardori
    if (subtotal < 50000) {
        const minEl = document.getElementById('min-order-warning');
        if (minEl) {
            minEl.style.display = 'block';
            minEl.textContent = `⚠️ Minimal buyurtma: 50 000 UZS (yana ${Number(50000 - subtotal).toLocaleString()} UZS qo'shing)`;
        }
    }
}

// Promo kod
function applyPromoCode() {
    const input = document.getElementById('promo-input');
    const code = input ? input.value.trim().toUpperCase() : '';
    if (!code) return;

    const promoCodes = {
        'NURAFSHON10': 10,
        'CHEGIRMA15': 15,
        'YANGI20': 20,
    };

    const discount = promoCodes[code];
    if (discount) {
        localStorage.setItem('promo_discount', discount);
        localStorage.setItem('promo_code', code);
        haptic('success');
        showToast(`🎉 Promo kod qo'llandi! -${discount}% chegirma`, 'success');
        loadCart();
    } else {
        haptic('error');
        showToast("Noto'g'ri promo kod", 'error');
    }
}

function updateQuantity(index, change) {
    const cart = getCart();
    cart[index].quantity += change;
    if (cart[index].quantity <= 0) cart.splice(index, 1);
    saveCart(cart);
    loadCart();
}

function removeFromCart(index) {
    haptic('light');
    const cart = getCart();
    const name = cart[index].name;
    cart.splice(index, 1);
    saveCart(cart);
    loadCart();
    showToast(`${name} savatdan olib tashlandi`, 'info');
}

// ─── Checkout ─────────────────────────────────────────────────
function loadCheckout() {
    const container = document.getElementById('checkout-items');
    const subtotalEl = document.getElementById('checkout-subtotal');
    const deliveryEl = document.getElementById('checkout-delivery');
    const totalEl = document.getElementById('checkout-total');
    if (!container) return;

    const cart = getCart();
    if (cart.length === 0) { window.location.href = 'katalog.html'; return; }

    container.innerHTML = '';
    let subtotal = 0;

    cart.forEach(item => {
        const itemTotal = item.price * item.quantity;
        subtotal += itemTotal;
        container.innerHTML += `
        <div class="flex items-center gap-4 border-b border-surface-container-high pb-4 mb-4 last:border-0 last:mb-0">
            <div class="w-16 h-16 rounded-xl bg-surface-container-low overflow-hidden flex-shrink-0">
                <img class="w-full h-full object-cover" src="${item.image}" alt="${item.name}">
            </div>
            <div class="flex-1">
                <h4 class="font-label-md text-label-md text-on-surface">${item.name}</h4>
                <div class="flex justify-between items-center mt-2">
                    <span class="font-bold text-primary">${Number(itemTotal).toLocaleString()} UZS</span>
                    <span class="text-on-surface-variant text-sm bg-surface-container px-2 py-1 rounded-lg">x${item.quantity}</span>
                </div>
            </div>
        </div>`;
    });

    const promoDiscount = parseInt(localStorage.getItem('promo_discount') || '0');
    const discountAmount = Math.round(subtotal * promoDiscount / 100);
    const deliveryFee = subtotal >= 150000 ? 0 : 15000;
    const total = subtotal - discountAmount + deliveryFee;

    if (subtotalEl) subtotalEl.textContent = `${Number(subtotal).toLocaleString()} UZS`;
    if (deliveryEl) deliveryEl.textContent = deliveryFee === 0 ? 'Bepul 🎉' : `${Number(deliveryFee).toLocaleString()} UZS`;

    const discountRow = document.getElementById('checkout-discount-row');
    if (discountRow && promoDiscount > 0) {
        discountRow.style.display = 'flex';
        const discountEl2 = document.getElementById('checkout-discount');
        if (discountEl2) discountEl2.textContent = `-${Number(discountAmount).toLocaleString()} UZS`;
    }

    if (totalEl) totalEl.textContent = `${Number(total).toLocaleString()} UZS`;
}

// To'lov turi tanlash
function selectPayment(type, btn) {
    document.querySelectorAll('.payment-btn').forEach(b => {
        b.classList.remove('border-primary', 'bg-primary/5');
        b.classList.add('border-outline-variant');
    });
    btn.classList.add('border-primary', 'bg-primary/5');
    btn.classList.remove('border-outline-variant');
    localStorage.setItem('payment_type', type);
    haptic('light');
}

// Yetkazish vaqti tanlash
function selectTimeSlot(slot, btn) {
    document.querySelectorAll('.timeslot-btn').forEach(b => {
        b.classList.remove('bg-primary', 'text-white');
        b.classList.add('bg-surface-container-low', 'text-on-surface');
    });
    btn.classList.add('bg-primary', 'text-white');
    btn.classList.remove('bg-surface-container-low', 'text-on-surface');
    localStorage.setItem('delivery_slot', slot);
    haptic('light');
}

async function submitOrder() {
    const cart = getCart();
    if (cart.length === 0) return;

    const items = cart.map(item => ({ product_variant_id: item.id, quantity: item.quantity }));
    const addressInput = document.querySelector('#address-input');
    const address = addressInput ? addressInput.value.trim() : '';

    if (!address) {
        haptic('error');
        showToast("Iltimos, manzilni kiriting", 'warning');
        return;
    }

    const paymentType = localStorage.getItem('payment_type') || 'cash';
    const promoCode = localStorage.getItem('promo_code') || '';
    const deliverySlot = localStorage.getItem('delivery_slot') || '';

    const submitBtn = document.getElementById('submit-order-btn');
    if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = 'Yuborilmoqda...'; }

    try {
        const response = await fetchAPI('/orders/', {
            method: 'POST',
            body: JSON.stringify({ items, address, payment_type: paymentType, promo_code: promoCode, delivery_slot: deliverySlot })
        });

        localStorage.removeItem('cart');
        localStorage.removeItem('promo_discount');
        localStorage.removeItem('promo_code');
        haptic('success');

        if (response.payment_url) {
            if (tg) tg.openLink(response.payment_url);
            else window.location.href = response.payment_url;
        } else {
            window.location.href = 'tasdiqlandi.html';
        }
    } catch (e) {
        haptic('error');
        showToast("Xatolik yuz berdi. Qayta urinib ko'ring.", 'error');
        if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = 'Buyurtma berish'; }
    }
}

// ─── Buyurtmalar ──────────────────────────────────────────────
const STATUS_LABELS = {
    yangi: { label: 'Yangi', emoji: '🆕', color: 'text-blue-500' },
    tayyorlanmoqda: { label: 'Tayyorlanmoqda', emoji: '👨‍🍳', color: 'text-orange-500' },
    yolda: { label: 'Yo\'lda', emoji: '🚚', color: 'text-yellow-600' },
    yetkazildi: { label: 'Yetkazildi', emoji: '✅', color: 'text-green-600' },
    bekor_qilindi: { label: 'Bekor qilindi', emoji: '❌', color: 'text-red-500' },
};

async function loadOrders() {
    const container = document.getElementById('orders-container');
    if (!container) return;
    container.innerHTML = `<div class="text-center py-8 text-on-surface-variant">
        <div class="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full mx-auto mb-3"></div>
        Yuklanmoqda...</div>`;

    try {
        const orders = await fetchAPI('/orders/');
        if (orders.length === 0) {
            container.innerHTML = `
            <div class="flex flex-col items-center justify-center py-16 text-center">
                <span class="text-6xl mb-4">📦</span>
                <h3 class="font-bold text-on-surface text-lg mb-2">Buyurtmalar yo'q</h3>
                <p class="text-on-surface-variant mb-6">Hali biror narsa buyurtma qilmadingiz</p>
                <a href="katalog.html" class="bg-primary text-white px-6 py-3 rounded-xl font-semibold">🛍 Xarid qilish</a>
            </div>`;
            return;
        }

        container.innerHTML = orders.map(order => {
            const date = new Date(order.created_at).toLocaleDateString('uz-UZ', { day: '2-digit', month: 'long', year: 'numeric' });
            const st = STATUS_LABELS[order.status] || { label: order.status, emoji: '📋', color: 'text-on-surface' };
            return `
            <div class="bg-surface-container-lowest rounded-2xl p-4 mb-3 border border-outline-variant/20 shadow-sm">
                <div class="flex justify-between items-center mb-3">
                    <span class="font-bold text-on-surface text-base">Buyurtma #${order.id}</span>
                    <span class="text-xs text-on-surface-variant">${date}</span>
                </div>
                <div class="flex justify-between items-center">
                    <div class="flex items-center gap-2">
                        <span class="text-lg">${st.emoji}</span>
                        <span class="font-semibold text-sm ${st.color}">${st.label}</span>
                    </div>
                    <span class="font-bold text-primary">${Number(order.total_amount).toLocaleString()} UZS</span>
                </div>
                ${order.status === 'yolda' ? `
                <div class="mt-3 bg-yellow-50 rounded-xl p-3 flex items-center gap-2">
                    <span class="text-xl">🚚</span>
                    <span class="text-sm text-yellow-800 font-medium">Buyurtmangiz yo'lda!</span>
                </div>` : ''}
            </div>`;
        }).join('');
    } catch (e) {
        container.innerHTML = `<div class="text-center py-8 text-error">
            <span class="text-4xl mb-3 block">⚠️</span>
            Yuklab bo'lmadi. Qayta urining.</div>`;
    }
}

// ─── API Fetch ────────────────────────────────────────────────
async function fetchAPI(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers = {
        'Content-Type': 'application/json',
        'Telegram-Data': initData,
    };
    if (options.headers) Object.assign(headers, options.headers);

    const response = await fetch(url, { ...options, headers });
    if (!response.ok) {
        console.error('API Error:', response.status, await response.text());
        throw new Error(`API Error: ${response.status}`);
    }
    return response.json();
}
