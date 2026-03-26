from rest_framework import serializers
from .models import (
    Category, MenuItem, Table, Reservation, Order, OrderItem, Cart, CartItem
)


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model."""

    class Meta:
        model = Category
        fields = ['id', 'name']


class MenuItemSerializer(serializers.ModelSerializer):
    """Serializer for MenuItem model."""
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = MenuItem
        fields = [
            'id', 'name', 'description', 'price', 'category',
            'category_name', 'is_available', 'image'
        ]


class TableSerializer(serializers.ModelSerializer):
    """Serializer for Table model."""

    class Meta:
        model = Table
        fields = ['id', 'number', 'capacity', 'is_available']


class ReservationSerializer(serializers.ModelSerializer):
    """Serializer for Reservation model."""
    table_number = serializers.IntegerField(source='table.number', read_only=True)

    class Meta:
        model = Reservation
        fields = [
            'id', 'table', 'table_number', 'customer_name', 'customer_email',
            'customer_phone', 'date', 'party_size', 'status', 'created_at', 'notes'
        ]

    def validate_date(self, value):
        """Ensure reservation is for future."""
        from django.utils import timezone
        if value < timezone.now():
            raise serializers.ValidationError('Reservation must be in the future.')
        return value

    def validate_party_size(self, value):
        """Ensure party size doesn't exceed table capacity."""
        table = self.initial_data.get('table')
        if table:
            try:
                table_obj = Table.objects.get(pk=table)
                if value > table_obj.capacity:
                    raise serializers.ValidationError(
                        f'Party size exceeds table capacity of {table_obj.capacity}.'
                    )
            except Table.DoesNotExist:
                pass
        return value


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for OrderItem model."""
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    menu_item_price = serializers.DecimalField(
        source='menu_item.price', max_digits=6, decimal_places=2, read_only=True
    )

    class Meta:
        model = OrderItem
        fields = ['id', 'menu_item', 'menu_item_name', 'menu_item_price', 'quantity', 'subtotal']


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order model."""
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'customer_name', 'customer_email', 'customer_phone',
            'total', 'status', 'created_at', 'updated_at', 'notes', 'items'
        ]


class CreateOrderSerializer(serializers.Serializer):
    """Serializer for creating an order."""
    customer_name = serializers.CharField(max_length=200)
    customer_email = serializers.EmailField()
    customer_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    items = serializers.ListField(
        child=serializers.DictField(
            child=serializers.IntegerField()
        )
    )

    def validate_items(self, value):
        """Validate items list."""
        if not value:
            raise serializers.ValidationError('Order must have at least one item.')
        for item in value:
            if 'menu_item' not in item or 'quantity' not in item:
                raise serializers.ValidationError('Each item must have menu_item and quantity.')
            if item['quantity'] < 1:
                raise serializers.ValidationError('Quantity must be at least 1.')
        return value


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for CartItem model."""
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    menu_item_price = serializers.DecimalField(
        source='menu_item.price', max_digits=6, decimal_places=2, read_only=True
    )
    subtotal = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = CartItem
        fields = ['id', 'menu_item', 'menu_item_name', 'menu_item_price', 'quantity', 'subtotal']


class CartSerializer(serializers.ModelSerializer):
    """Serializer for Cart model."""
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'session_key', 'created_at', 'updated_at', 'items', 'total', 'item_count']


class AddToCartSerializer(serializers.Serializer):
    """Serializer for adding item to cart."""
    menu_item = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)