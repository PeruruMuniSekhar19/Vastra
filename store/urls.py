from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('shop/', views.shop, name='shop'),
    path('product/<int:id>/', views.product_detail, name='product'),
    path('cart/', views.cart, name='cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.orders, name='orders'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('return/<int:order_id>/', views.request_return, name='request_return'),
    path('profile/', views.profile_view, name='profile'),
    
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/toggle/<int:product_id>/', views.wishlist_toggle, name='wishlist_toggle'),
    path('add_to_wishlist/<int:id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('remove_from_wishlist/<int:id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('wishlist/add/<int:id>/', views.add_to_wishlist, name='add_to_wishlist_alt'), # backup
    
    path('my-orders/', views.orders, name='my_orders'),
    path('invoice/<str:txn_id>/', views.download_invoice, name='download_invoice'),
    path('review/<int:product_id>/', views.add_review, name='add_review'),
    path('order_success/', views.order_success, name='order_success'),
]