from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventViewSet, OrderViewSet, CategoryViewSet

router = DefaultRouter()
router.register(r'events', EventViewSet)
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'categories', CategoryViewSet)

urlpatterns = [
    path('', include(router.urls)),
]