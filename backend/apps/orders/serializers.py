"""Serializers for the orders app."""
from django.conf import settings
from rest_framework import serializers

from apps.accounts.serializers import AddressSerializer
from apps.catalog.models import ProductVariant

from .models import Order, OrderItem


# ─── OrderItem ────────────────────────────────────────────────────────────────

class OrderItemInputSerializer(serializers.Serializer):
    """Used only during order creation — takes variant_id + quantity."""

    variant_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, max_value=99)

    def validate(self, data):
        try:
            variant = ProductVariant.objects.select_related('product').get(
                pk=data['variant_id'], is_available=True
            )
        except ProductVariant.DoesNotExist:
            raise serializers.ValidationError(
                {'variant_id': f"Variant #{data['variant_id']} mavjud emas yoki sotuvda yo'q."}
            )
        data['_variant'] = variant
        return data


class OrderItemSerializer(serializers.ModelSerializer):
    """Read-only representation of an order line item."""

    line_total = serializers.IntegerField(read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'product_name_snapshot', 'variant_weight_snapshot',
            'quantity', 'price_at_order', 'line_total',
        ]


# ─── Order ────────────────────────────────────────────────────────────────────

class OrderCreateSerializer(serializers.Serializer):
    """Accepts the full order payload from the Mini App."""

    items = OrderItemInputSerializer(many=True, min_length=1)
    delivery_type = serializers.ChoiceField(choices=Order.DeliveryType.choices)
    address_id = serializers.IntegerField(required=False, allow_null=True)
    delivery_time_slot = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=''
    )
    payment_method = serializers.ChoiceField(choices=Order.PaymentMethod.choices)
    comment = serializers.CharField(
        max_length=1000, required=False, allow_blank=True, default=''
    )

    def validate(self, data):
        if (
            data.get('delivery_type') == Order.DeliveryType.DELIVERY
            and not data.get('address_id')
        ):
            raise serializers.ValidationError(
                {'address_id': 'Yetkazib berish uchun manzil majburiy.'}
            )
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        items_data = validated_data.pop('items')
        address_id = validated_data.pop('address_id', None)

        # Resolve address (must belong to this user)
        address = None
        if address_id:
            from apps.accounts.models import Address
            try:
                address = Address.objects.get(pk=address_id, user=user)
            except Address.DoesNotExist:
                raise serializers.ValidationError({'address_id': 'Manzil topilmadi.'})

        # Resolve delivery_time_slot
        time_slot_str = validated_data.pop('delivery_time_slot', '')
        time_slot_obj = None
        if time_slot_str:
            from .models import DeliveryTimeSlot
            try:
                time_slot_obj = DeliveryTimeSlot.objects.get(id=int(time_slot_str))
            except (ValueError, DeliveryTimeSlot.DoesNotExist):
                time_slot_obj = DeliveryTimeSlot.objects.filter(label=time_slot_str).first()

        # Delivery fee: only for delivery type
        delivery_fee = (
            settings.DEFAULT_DELIVERY_FEE
            if validated_data.get('delivery_type') == Order.DeliveryType.DELIVERY
            else 0
        )

        order = Order.objects.create(
            user=user,
            address=address,
            delivery_fee=delivery_fee,
            delivery_time_slot=time_slot_obj,
            **validated_data,
        )

        # Create items — prices always from DB, never from frontend
        subtotal = 0
        for item_data in items_data:
            variant = item_data['_variant']
            qty = item_data['quantity']
            price = variant.price

            # Apply product-level discount
            discount = variant.product.discount_percent
            if discount:
                price = int(price * (100 - discount) / 100)

            OrderItem.objects.create(
                order=order,
                variant=variant,
                product_name_snapshot=variant.product.name,
                variant_weight_snapshot=variant.label,
                quantity=qty,
                price_at_order=price,
            )
            subtotal += price * qty

        order.subtotal = subtotal
        order.total = subtotal + delivery_fee
        order.save(update_fields=['subtotal', 'total'])

        return order


class OrderListSerializer(serializers.ModelSerializer):
    """Compact order summary for list view."""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(
        source='get_payment_status_display', read_only=True
    )
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'status', 'status_display',
            'delivery_type', 'payment_method',
            'payment_status', 'payment_status_display',
            'subtotal', 'delivery_fee', 'total',
            'items_count', 'created_at',
        ]

    def get_items_count(self, obj):
        return obj.total_items


class OrderDetailSerializer(serializers.ModelSerializer):
    """Full order detail including items and address."""

    items = OrderItemSerializer(many=True, read_only=True)
    address = AddressSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(
        source='get_payment_status_display', read_only=True
    )

    class Meta:
        model = Order
        fields = [
            'id', 'status', 'status_display',
            'delivery_type', 'address', 'delivery_time_slot',
            'payment_method', 'payment_status', 'payment_status_display',
            'subtotal', 'delivery_fee', 'total',
            'comment', 'items', 'created_at', 'updated_at',
        ]
