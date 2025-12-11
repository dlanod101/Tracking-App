from django.urls import path
from .views import (
    index, login_view, register_view, dashboard, logout_view, 
    create_order, track_order, update_location, get_order_location,
    dispatch_dashboard, accept_order, dispatch_tracking, complete_delivery
)

urlpatterns = [
    path('', index, name='home'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('dashboard/', dashboard, name='dashboard'),
    path('create-order/', create_order, name='create_order'),
    path('track/<int:order_id>/', track_order, name='track_order'),
    
    # Dispatch Rider URLs
    path('dispatch/', dispatch_dashboard, name='dispatch_dashboard'),
    path('dispatch/accept/<int:order_id>/', accept_order, name='accept_order'),
    path('dispatch/tracking/<int:order_id>/', dispatch_tracking, name='dispatch_tracking'),
    path('dispatch/complete/<int:order_id>/', complete_delivery, name='complete_delivery'),
    
    # API endpoints
    path('api/update-location/<int:order_id>/', update_location, name='update_location'),
    path('api/get-location/<int:order_id>/', get_order_location, name='get_order_location'),
    path('logout/', logout_view, name='logout'),
]