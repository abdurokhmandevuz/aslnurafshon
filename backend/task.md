# Task List: MVP Extension

- [x] **Block 6: Inventory Automation & Low Stock Alerts**
  - [x] Add `last_low_stock_notified` to `ProductVariant` model
  - [x] Override `ProductVariant.save()` logic (set `is_available = False` if `stock_qty <= 0`, reset `last_low_stock_notified` if `stock_qty > 3`)
  - [x] Update signals to trigger low stock Telegram alert once when `stock_qty <= 3`
  - [x] Create and run local migrations

- [x] **Block 5: Dynamic Banner & Daily Deal**
  - [x] Modify `Banner` model to add schedule and button fields
  - [x] Create `DailyDeal` model
  - [x] Register Banner & DailyDeal in Admin with editable `is_active`
  - [x] Update homepage `catalog_view` to load dynamic banners & active daily deal
  - [x] Display daily deal with JS countdown timer on homepage
  - [x] Create and run migrations

- [x] **Block 4: Delivery Time Slots**
  - [x] Create `DeliveryTimeSlot` model
  - [x] Link `Order` to `DeliveryTimeSlot`
  - [x] Retrieve active time slots with capacity check in `checkout_view`
  - [x] Handle selected time slot in `checkout_submit_view`
  - [x] Add slot selector dropdown/UI in `checkout.html`
  - [x] Create and run migrations

- [x] **Block 3: Product Reviews**
  - [x] Create `ProductReview` model with `rating` and `comment`
  - [x] Add review statistics properties to `Product` model
  - [x] Display average rating & reviews list on product detail page
  - [x] Allow customers with delivered order items to submit reviews
  - [x] Add `submit_review_view` route
  - [x] Create and run migrations

- [x] **Block 7: PDF Receipt Generation**
  - [x] Implement `generate_receipt_pdf` utility using ReportLab
  - [x] Bind PDF generation to `yetkazildi` order status change
  - [x] Send generated PDF to client via Telegram bot
  - [x] Create bot command `/chek` / button to download receipt

- [ ] **Block 1: Gift Sets & Bundles**
  - [ ] Create `ProductBundle` and `BundleItem` models
  - [ ] Link `OrderItem` to `ProductBundle`
  - [ ] Render "To'plamlar" category and bundle detail page
  - [ ] Handle bundle purchase decomposition during checkout
  - [ ] Add `related_products` M2M to `Product` and render on detail page
  - [ ] Create and run migrations

- [ ] **Block 2: Corporate/Wholesale Inquiries**
  - [ ] Create `CorporateInquiry` model
  - [ ] Create corporate inquiry form template (`corporate.html`)
  - [ ] Handle inquiry POST submissions and notify admins via bot
  - [ ] Create and run migrations

- [ ] **Block 8: CRM-Lite Segmentations & Broadcast**
  - [ ] Annotate `TelegramUser` model with spent & activity metrics
  - [ ] Customize `TelegramUserAdmin` with fields, filters, and custom message broadcast action
  - [ ] Create and run migrations
