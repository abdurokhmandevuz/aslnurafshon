"""URL configuration for catalog app."""
from django.urls import path

from .views import CategoryListView, ProductDetailView, ProductListView, HomeAPIView

urlpatterns = [
    path('home/', HomeAPIView.as_view(), name='home'),
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
]
