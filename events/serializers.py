from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import Event, Ticket, Order, OrderItem, Category


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name']
        read_only_fields = ['id']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id', 'username', 'email', 'first_name', 'last_name']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']
        read_only_fields = ['id', 'name']


class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ['id', 'name', 'price', 'quantity_available']
        read_only_fields = ['id', 'name', 'price', 'quantity_available']


class EventSerializer(serializers.ModelSerializer):
    organizer = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )
    tickets = TicketSerializer(many=True, read_only=True)

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'description', 'date', 'location',
            'organizer', 'category', 'category_id', 'is_active',
            'created_at', 'updated_at', 'tickets', 'available_tickets'
        ]
        read_only_fields = ['id', 'organizer', 'created_at', 'updated_at', 'available_tickets']


class OrderItemSerializer(serializers.ModelSerializer):
    ticket = TicketSerializer(read_only=True)
    ticket_id = serializers.PrimaryKeyRelatedField(
        queryset=Ticket.objects.all(), source='ticket', write_only=True
    )

    class Meta:
        model = OrderItem
        fields = ['id', 'ticket', 'ticket_id', 'quantity']
        read_only_fields = ['id']


class OrderSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    order_items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'total_price', 'status', 'created_at',
            'order_items'
        ]
        read_only_fields = ['id', 'user', 'total_price', 'created_at', 'status']


class OrderCreateSerializer(serializers.Serializer):
    ticket_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)

    def validate(self, data):
        ticket_id = data['ticket_id']
        quantity = data['quantity']

        try:
            ticket = Ticket.objects.get(id=ticket_id)
        except Ticket.DoesNotExist:
            raise serializers.ValidationError("Ticket does not exist")

        if ticket.quantity_available < quantity:
            raise serializers.ValidationError(
                f"Not enough tickets available. Available: {ticket.quantity_available}"
            )

        data['ticket'] = ticket
        return data