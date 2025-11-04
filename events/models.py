from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateTimeField()
    location = models.CharField(max_length=200)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_events')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    @property
    def available_tickets(self):
        return self.tickets.filter(quantity_available__gt=0)


class Ticket(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='tickets')
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    quantity_available = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.event.title}"

    class Meta:
        ordering = ['price']


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"

    def calculate_total_price(self):
        total = Decimal('0.00')
        for item in self.order_items.all():
            total += item.ticket.price * item.quantity
        return total

    def confirm_order(self):
        """Confirm order and finalize ticket allocation"""
        if self.status == 'pending':
            self.status = 'completed'
            self.save()
            return True
        return False

    def cancel_order(self):
        """Cancel order and restore ticket quantities"""
        if self.status == 'pending':
            for order_item in self.order_items.all():
                order_item.ticket.quantity_available += order_item.quantity
                order_item.ticket.save()
            self.status = 'canceled'
            self.save()
            return True
        return False

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"

    def calculate_total_price(self):
        total = Decimal('0.00')
        for item in self.order_items.all():
            total += item.ticket.price * item.quantity
        return total


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.quantity} x {self.ticket.name}"

    def save(self, *args, **kwargs):
        # Update ticket availability when order item is created
        if self.pk is None:  # New order item
            if self.ticket.quantity_available < self.quantity:
                raise ValueError(
                    f"Not enough tickets available. Available: {self.ticket.quantity_available}, Requested: {self.quantity}")
            self.ticket.quantity_available -= self.quantity
            self.ticket.save()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Restore ticket availability when order item is deleted
        self.ticket.quantity_available += self.quantity
        self.ticket.save()
        super().delete(*args, **kwargs)