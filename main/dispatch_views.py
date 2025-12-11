# Dispatch Rider Views and Functionality
# This file contains additional views for dispatch rider features
# To be added to main/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Order, UserProfile, LocationUpdate

# Updated register_view - replace existing one
def register_view(request):
    """Registration page for new users"""
    if request.user.is_authenticated:
        # Check user type and redirect accordingly
        if hasattr(request.user, 'profile') and request.user.profile.user_type == 'dispatch':
            return redirect('dispatch_dashboard')
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        user_type = request.POST.get('user_type', 'user')
        
        # Get dispatch-specific fields
        phone_number = request.POST.get('phone_number', '')
        vehicle_type = request.POST.get('vehicle_type', '')
        license_number = request.POST.get('license_number', '')
        
        if password != password2:
            messages.error(request, 'Passwords do not match.')
            return redirect('register')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('register')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return redirect('register')
        
        # Additional validation for dispatch riders
        if user_type == 'dispatch':
            if not phone_number or not vehicle_type:
                messages.error(request, 'Phone number and vehicle type are required for dispatch riders.')
                return redirect('register')
        
        from django.contrib.auth import login as auth_login
        from django.contrib.auth.models import User
        
        user = User.objects.create_user(username=username, email=email, password=password)
        
        # Update user profile
        profile = user.profile
        profile.user_type = user_type
        profile.phone_number = phone_number
        if user_type == 'dispatch':
            profile.vehicle_type = vehicle_type
            profile.license_number = license_number
        profile.save()
        
        auth_login(request, user)
        messages.success(request, f'Welcome, {user.username}! Your account has been created.')
        
        # Redirect based on user type
        if user_type == 'dispatch':
            return redirect('dispatch_dashboard')
        return redirect('dashboard')
    
    return render(request, 'register.html')

# Updated login_view - replace existing one
def login_view(request):
    """Login page for users"""
    from django.contrib.auth import login as auth_login, authenticate
    
    if request.user.is_authenticated:
        # Check user type and redirect accordingly
        if hasattr(request.user, 'profile') and request.user.profile.user_type == 'dispatch':
            return redirect('dispatch_dashboard')
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            
            # Redirect based on user type
            if hasattr(user, 'profile') and user.profile.user_type == 'dispatch':
                return redirect('dispatch_dashboard')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
            return redirect('login')
    return render(request, 'login.html')

# Dispatch Dashboard
@login_required(login_url='login')
def dispatch_dashboard(request):
    """Dashboard for dispatch riders"""
    # Check if user is dispatch rider
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'dispatch':
        messages.error(request, 'Access denied. This area is for dispatch riders only.')
        return redirect('dashboard')
    
    profile = request.user.profile
    
    # Get assigned orders
    assigned_orders = Order.objects.filter(assigned_dispatch=request.user).order_by('-date_created')
    
    # Get available orders (pending, not assigned)
    available_orders = Order.objects.filter(status='pending', assigned_dispatch__isnull=True).order_by('-date_created')
    
    # Statistics
    stats = {
        'total_deliveries': profile.total_deliveries,
        'active_orders': assigned_orders.filter(status='dispatched').count(),
        'completed_today': assigned_orders.filter(status='delivered', date_created__date=timezone.now().date()).count(),
        'rating': profile.rating,
    }
    
    context = {
        'profile': profile,
        'assigned_orders': assigned_orders[:10],  # Last 10
        'available_orders': available_orders[:20],  # Top 20 available
        'stats': stats,
    }
    
    return render(request, 'dispatch_dashboard.html', context)

# Accept Order
@login_required(login_url='login')
def accept_order(request, order_id):
    """Dispatch rider accepts an order"""
    # Check if user is dispatch rider
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'dispatch':
        messages.error(request, 'Only dispatch riders can accept orders.')
        return redirect('dashboard')
    
    order = get_object_or_404(Order, id=order_id)
    
    # Check if order is available
    if order.assigned_dispatch is not None:
        messages.error(request, 'This order has already been accepted by another dispatch rider.')
        return redirect('dispatch_dashboard')
    
    if order.status != 'pending':
        messages.error(request, 'This order is no longer available.')
        return redirect('dispatch_dashboard')
    
    # Assign order to dispatch rider
    order.assigned_dispatch = request.user
    order.status = 'dispatched'
    order.accepted_at = timezone.now()
    order.save()
    
    messages.success(request, f'Order #{order.id} accepted! Start your delivery.')
    return redirect('dispatch_tracking', order_id=order.id)

# Dispatch Tracking (for rider to update their location)
@login_required(login_url='login')
def dispatch_tracking(request, order_id):
    """Dispatch rider tracking interface for active delivery"""
    # Check if user is dispatch rider
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'dispatch':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    order = get_object_or_404(Order, id=order_id, assigned_dispatch=request.user)
    
    context = {
        'order': order,
    }
    
    return render(request, 'dispatch_tracking.html', context)

# Complete Delivery
@login_required(login_url='login')
def complete_delivery(request, order_id):
    """Mark delivery as complete"""
    # Check if user is dispatch rider
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'dispatch':
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    order = get_object_or_404(Order, id=order_id, assigned_dispatch=request.user)
    
    if order.status == 'delivered':
        messages.info(request, 'This order is already marked as delivered.')
        return redirect('dispatch_dashboard')
    
    order.status = 'delivered'
    order.save()
    
    # Update dispatch rider stats
    profile = request.user.profile
    profile.total_deliveries += 1
    profile.save()
    
    messages.success(request, f'Order #{order.id} marked as delivered! Great job!')
    return redirect('dispatch_dashboard')
