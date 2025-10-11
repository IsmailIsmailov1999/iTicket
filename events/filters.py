import django_filters
from .models import Event
from django.db.models import Q


class EventFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name='category__name')
    date_from = django_filters.DateTimeFilter(field_name='date', lookup_expr='gte')
    date_to = django_filters.DateTimeFilter(field_name='date', lookup_expr='lte')
    min_price = django_filters.NumberFilter(method='filter_min_price')
    max_price = django_filters.NumberFilter(method='filter_max_price')

    class Meta:
        model = Event
        fields = ['category', 'date_from', 'date_to']

    def filter_min_price(self, queryset, name, value):
        return queryset.filter(tickets__price__gte=value).distinct()

    def filter_max_price(self, queryset, name, value):
        return queryset.filter(tickets__price__lte=value).distinct()