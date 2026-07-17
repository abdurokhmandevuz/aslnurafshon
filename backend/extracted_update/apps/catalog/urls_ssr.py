from django.urls import path
from .views_ssr import catalog_view, product_detail_view

urlpatterns = [
    path('catalog/', catalog_view, name='catalog'),
    path('product/<int:pk>/', product_detail_view, name='product_detail'),
]
