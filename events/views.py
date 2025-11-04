from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q
from .models import Event, Ticket, Order, Category, OrderItem  # Добавлен OrderItem
from .serializers import (
    EventSerializer, TicketSerializer, OrderSerializer,
    CategorySerializer, OrderCreateSerializer, UserRegistrationSerializer
)
from .filters import EventFilter
from .permissions import IsOrganizerOrReadOnly


class UserRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": "User created successfully",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAdminUser]


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.filter(is_active=True).select_related('organizer', 'category').prefetch_related('tickets')
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOrganizerOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = EventFilter
    search_fields = ['title', 'description']
    ordering_fields = ['date', 'created_at']
    ordering = ['-date']

    def perform_create(self, serializer):
        serializer.save(organizer=self.request.user)

    @action(detail=True, methods=['get'])
    def tickets(self, request, pk=None):
        event = self.get_object()
        tickets = event.tickets.filter(quantity_available__gt=0)
        serializer = TicketSerializer(tickets, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def categories(self, request):
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related(
            'order_items', 'order_items__ticket', 'order_items__ticket__event'
        ).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(data=request.data, many=True)

        if serializer.is_valid():
            order_items_data = []
            total_price = 0

            for item_data in serializer.validated_data:
                ticket = item_data['ticket']
                quantity = item_data['quantity']

                order_items_data.append({
                    'ticket': ticket,
                    'quantity': quantity
                })
                total_price += float(ticket.price) * quantity

            # Create order with pending status
            order = Order.objects.create(
                user=request.user,
                total_price=total_price,
                status='pending'  # Changed from 'completed' to 'pending'
            )

            # Create order items
            for item_data in order_items_data:
                OrderItem.objects.create(
                    order=order,
                    ticket=item_data['ticket'],
                    quantity=item_data['quantity']
                )

            order_serializer = OrderSerializer(order, context={'request': request})
            return Response(order_serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm and complete the order (simulate payment)"""
        order = self.get_object()

        if order.user != request.user:
            return Response({"error": "Not your order"}, status=status.HTTP_403_FORBIDDEN)

        if order.status != 'pending':
            return Response({"error": "Order already processed"}, status=status.HTTP_400_BAD_REQUEST)

        # In a real application, this would integrate with a payment gateway
        # For now, we'll just mark it as completed
        order.status = 'completed'
        order.save()

        return Response({
            "message": "Order confirmed successfully",
            "order_id": order.id,
            "status": order.status
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a pending order"""
        order = self.get_object()

        if order.user != request.user:
            return Response({"error": "Not your order"}, status=status.HTTP_403_FORBIDDEN)

        if order.status != 'pending':
            return Response({"error": "Only pending orders can be canceled"}, status=status.HTTP_400_BAD_REQUEST)

        # Restore ticket quantities
        for order_item in order.order_items.all():
            order_item.ticket.quantity_available += order_item.quantity
            order_item.ticket.save()

        order.status = 'canceled'
        order.save()

        return Response({
            "message": "Order canceled successfully",
            "order_id": order.id,
            "status": order.status
        })