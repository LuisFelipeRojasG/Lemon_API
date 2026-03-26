from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from .models import Category, MenuItem, Table, Reservation, Order, OrderItem
from .serializer import (
    CategorySerializer, MenuItemSerializer, TableSerializer,
    ReservationSerializer, OrderSerializer, OrderItemSerializer,
    CreateOrderSerializer, CartSerializer, CartItemSerializer,
    AddToCartSerializer
)


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for Category model."""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class MenuItemViewSet(viewsets.ModelViewSet):
    """ViewSet for MenuItem model."""

    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer

    def get_queryset(self):
        """Filter by availability."""
        queryset = super().get_queryset()
        available = self.request.query_params.get('available')
        if available:
            queryset = queryset.filter(is_available=True)
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        return queryset


class TableViewSet(viewsets.ModelViewSet):
    """ViewSet for Table model."""

    queryset = Table.objects.all()
    serializer_class = TableSerializer

    def get_queryset(self):
        """Filter by availability."""
        queryset = super().get_queryset()
        available = self.request.query_params.get('available')
        if available:
            queryset = queryset.filter(is_available=True)
        return queryset

    @action(detail=True, methods=['get'])
    def available_slots(self, request, pk=None):
        """Get available time slots for a table."""
        table = self.get_object()
        date_str = request.query_params.get('date')

        if not date_str:
            return Response(
                {'error': 'Date parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from datetime import datetime
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reservations = Reservation.objects.filter(
            table=table,
            date__date=date,
            status__in=['pending', 'confirmed']
        )

        reserved_times = set()
        for res in reservations:
            reserved_times.add(res.date.hour)

        slots = []
        for hour in range(11, 22):
            if hour not in reserved_times:
                slots.append(f"{hour}:00")

        return Response({
            'table': table.number,
            'date': date_str,
            'available_slots': slots
        })


class ReservationViewSet(viewsets.ModelViewSet):
    """ViewSet for Reservation model."""

    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer

    def get_queryset(self):
        """Filter reservations."""
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        date_from = self.request.query_params.get('date_from')
        if date_from:
            from datetime import datetime
            try:
                dt = datetime.strptime(date_from, '%Y-%m-%d')
                queryset = queryset.filter(date__gte=dt)
            except ValueError:
                pass
        return queryset

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm a reservation."""
        reservation = self.get_object()
        reservation.status = 'confirmed'
        reservation.save()
        serializer = self.get_serializer(reservation)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a reservation."""
        reservation = self.get_object()
        reservation.status = 'cancelled'
        reservation.save()
        serializer = self.get_serializer(reservation)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def available_tables(self, request):
        """Find available tables for a given date/time and party size."""
        date_str = request.query_params.get('date')
        time_str = request.query_params.get('time')
        party_size = request.query_params.get('party_size')

        if not all([date_str, time_str, party_size]):
            return Response(
                {'error': 'date, time, and party_size parameters required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from datetime import datetime
            date_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            return Response(
                {'error': 'Invalid date/time format'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            party_size = int(party_size)
        except ValueError:
            return Response(
                {'error': 'Invalid party_size'},
                status=status.HTTP_400_BAD_REQUEST
            )

        tables = Table.objects.filter(
            capacity__gte=party_size,
            is_available=True
        )

        reserved_table_ids = Reservation.objects.filter(
            date__date=date_time.date(),
            date__hour=date_time.hour,
            status__in=['pending', 'confirmed']
        ).values_list('table_id', flat=True)

        available_tables = tables.exclude(id__in=reserved_table_ids)

        serializer = TableSerializer(available_tables, many=True)
        return Response(serializer.data)


class OrderViewSet(viewsets.ModelViewSet):
    """ViewSet for Order model."""

    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def get_queryset(self):
        """Filter orders."""
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    @action(detail=False, methods=['post'])
    def create_order(self, request):
        """Create a new order with items."""
        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            order = Order.objects.create(
                customer_name=serializer.validated_data['customer_name'],
                customer_email=serializer.validated_data['customer_email'],
                customer_phone=serializer.validated_data.get('customer_phone', ''),
                notes=serializer.validated_data.get('notes', ''),
                status='pending'
            )

            total = 0
            for item_data in serializer.validated_data['items']:
                menu_item = MenuItem.objects.get(pk=item_data['menu_item'])
                order_item = OrderItem.objects.create(
                    order=order,
                    menu_item=menu_item,
                    quantity=item_data['quantity']
                )
                total += order_item.subtotal

            order.total = total
            order.save()

        response_serializer = OrderSerializer(order)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """Mark order as paid."""
        order = self.get_object()
        order.status = 'paid'
        order.save()
        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an order."""
        order = self.get_object()
        order.status = 'cancelled'
        order.save()
        serializer = self.get_serializer(order)
        return Response(serializer.data)


class CartViewSet(viewsets.ModelViewSet):
    """ViewSet for Cart model."""

    serializer_class = CartSerializer

    def get_queryset(self):
        """Get cart for current session."""
        session_key = self.request.session.session_key
        if not session_key:
            self.request.session.create()
            session_key = self.request.session.session_key
        return Cart.objects.filter(session_key=session_key)

    def list(self, request, *args, **kwargs):
        """Get current cart or create one."""
        queryset = self.get_queryset()
        if not queryset.exists():
            cart = Cart.objects.create(session_key=request.session.session_key)
            serializer = self.get_serializer(cart)
            return Response(serializer.data)
        cart = queryset.first()
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """Add item to cart."""
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key

        cart, _ = Cart.objects.get_or_create(session_key=session_key)

        menu_item = MenuItem.objects.get(pk=serializer.validated_data['menu_item'])
        quantity = serializer.validated_data.get('quantity', 1)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            menu_item=menu_item,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def remove_item(self, request):
        """Remove item from cart."""
        item_id = request.data.get('item_id')
        if not item_id:
            return Response(
                {'error': 'item_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        session_key = request.session.session_key
        cart = Cart.objects.filter(session_key=session_key).first()

        if not cart:
            return Response(
                {'error': 'Cart not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
            cart_item.delete()
        except CartItem.DoesNotExist:
            return Response(
                {'error': 'Item not found in cart'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def update_item(self, request):
        """Update item quantity in cart."""
        item_id = request.data.get('item_id')
        quantity = request.data.get('quantity')

        if not item_id or quantity is None:
            return Response(
                {'error': 'item_id and quantity required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            quantity = int(quantity)
        except ValueError:
            return Response(
                {'error': 'Invalid quantity'},
                status=status.HTTP_400_BAD_REQUEST
            )

        session_key = request.session.session_key
        cart = Cart.objects.filter(session_key=session_key).first()

        if not cart:
            return Response(
                {'error': 'Cart not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if quantity <= 0:
            try:
                cart_item = CartItem.objects.get(id=item_id, cart=cart)
                cart_item.delete()
            except CartItem.DoesNotExist:
                return Response(
                    {'error': 'Item not found in cart'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            try:
                cart_item = CartItem.objects.get(id=item_id, cart=cart)
                cart_item.quantity = quantity
                cart_item.save()
            except CartItem.DoesNotExist:
                return Response(
                    {'error': 'Item not found in cart'},
                    status=status.HTTP_404_NOT_FOUND
                )

        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def checkout(self, request):
        """Create order from cart."""
        session_key = request.session.session_key
        cart = Cart.objects.filter(session_key=session_key).first()

        if not cart or not cart.items.exists():
            return Response(
                {'error': 'Cart is empty'},
                status=status.HTTP_400_BAD_REQUEST
            )

        customer_name = request.data.get('customer_name')
        customer_email = request.data.get('customer_email')
        customer_phone = request.data.get('customer_phone', '')
        notes = request.data.get('notes', '')

        if not customer_name or not customer_email:
            return Response(
                {'error': 'customer_name and customer_email required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            order = Order.objects.create(
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                notes=notes,
                total=cart.total,
                status='pending'
            )

            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    menu_item=cart_item.menu_item,
                    quantity=cart_item.quantity
                )

            cart.items.all().delete()

        response_serializer = OrderSerializer(order)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['delete'])
    def clear(self, request):
        """Clear cart."""
        session_key = request.session.session_key
        Cart.objects.filter(session_key=session_key).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)