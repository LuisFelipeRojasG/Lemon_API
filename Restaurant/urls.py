from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'category', views.CategoryViewSet, basename='category')
router.register(r'menu-item', views.MenuItemViewSet, basename='menu-item')
router.register(r'table', views.TableViewSet, basename='table')
router.register(r'reservation', views.ReservationViewSet, basename='reservation')
router.register(r'order', views.OrderViewSet, basename='order')
router.register(r'cart', views.CartViewSet, basename='cart')

urlpatterns = router.urls