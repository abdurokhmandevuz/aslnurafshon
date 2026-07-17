from django.urls import path
from .views_ssr import (
    catalog_view, product_detail_view, toggle_favorite_view, submit_review_view,
    product_by_barcode_view, bundle_detail_view
)

urlpatterns = [
    path('catalog/', catalog_view, name='catalog'),
    path('product/<int:pk>/', product_detail_view, name='product_detail'),
    path('bundle/<int:pk>/', bundle_detail_view, name='bundle_detail'),
    path('product/<int:product_id>/favorite/', toggle_favorite_view, name='toggle_favorite'),
    path('product/<int:product_id>/review/', submit_review_view, name='submit_review'),
    path('catalog/barcode/search/', product_by_barcode_view, name='product_by_barcode'),
]
