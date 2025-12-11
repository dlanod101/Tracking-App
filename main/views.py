from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from .models import Order, Delivery, UserProfile, LocationUpdate
from django.contrib.auth import login as auth_login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json

# Create your views here.

def index(request):
    """Landing page for the tracking application"""
    if request.user.is_authenticated:
        # Redirect based on user type
        if hasattr(request.user, 'profile') and request.user.profile.user_type == 'dispatch':
            return redirect('dispatch_dashboard')
        return redirect('dashboard')
    return render(request, 'index.html')

def login_view(request):
    """Login page for users"""
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

@login_required(login_url='login')
def dashboard(request):
    """Dashboard page for logged-in users"""
    orders = Order.objects.filter(user=request.user).order_by('-date_created')
    stats = {
        'total_orders': orders.count(),
        'pending': orders.filter(status='pending').count(),
        'dispatched': orders.filter(status='dispatched').count(),
        'delivered': orders.filter(status='delivered').count(),
    }
    context = {
        'orders': orders,
        'stats': stats,
    }
    return render(request, 'dashboard.html', context)

@login_required(login_url='login')
def create_order(request):
    """Create a new order"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        pickup_address = request.POST.get('pickup_address', '')
        pickup_lat = request.POST.get('pickup_latitude', '')
        pickup_lng = request.POST.get('pickup_longitude', '')
        delivery_address = request.POST.get('delivery_address', '')
        delivery_lat = request.POST.get('delivery_latitude', '')
        delivery_lng = request.POST.get('delivery_longitude', '')
        
        # Validation
        if not name or not description:
            messages.error(request, 'Please fill in all required fields.')
            return redirect('create_order')
        
        if len(name) < 3:
            messages.error(request, 'Order name must be at least 3 characters long.')
            return redirect('create_order')
        
        if len(description) < 10:
            messages.error(request, 'Order description must be at least 10 characters long.')
            return redirect('create_order')
        
        # Create the order
        order = Order.objects.create(
            user=request.user,
            name=name,
            description=description,
            status='pending',
            pickup_address=pickup_address if pickup_address else None,
            pickup_latitude=pickup_lat if pickup_lat else None,
            pickup_longitude=pickup_lng if pickup_lng else None,
            delivery_address=delivery_address if delivery_address else None,
            delivery_latitude=delivery_lat if delivery_lat else None,
            delivery_longitude=delivery_lng if delivery_lng else None,
        )
        
        messages.success(request, f'Order #{order.id} "{order.name}" has been created successfully!')
        return redirect('dashboard')
    
    return render(request, 'create_order.html')

@login_required(login_url='login')
def track_order(request, order_id):
    """Track an order with real-time location on map"""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        messages.error(request, 'Order not found.')
        return redirect('dashboard')
    
    # Get location history
    location_history = LocationUpdate.objects.filter(order=order)[:50]  # Last 50 updates
    
    context = {
        'order': order,
        'location_history': location_history,
    }
    return render(request, 'track_order.html', context)

@csrf_exempt  # In production, use proper CSRF handling
@require_http_methods(["POST"])
def update_location(request, order_id):
    """API endpoint to update delivery location (for delivery personnel/system)"""
    try:
        data = json.loads(request.body)
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        notes = data.get('notes', '')
        
        if not latitude or not longitude:
            return JsonResponse({'success': False, 'error': 'Missing coordinates'}, status=400)
        
        order = Order.objects.get(id=order_id)
        
        # Update current location
        order.current_latitude = latitude
        order.current_longitude = longitude
        order.last_location_update = timezone.now()
        order.save()
        
        # Create location history entry
        LocationUpdate.objects.create(
            order=order,
            latitude=latitude,
            longitude=longitude,
            notes=notes
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Location updated successfully',
            'last_update': order.last_location_update.isoformat()
        })
        
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required(login_url='login')
def get_order_location(request, order_id):
    """API endpoint to get current order location (for real-time updates)"""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        
        response_data = {
            'success': True,
            'order_id': order.id,
            'status': order.status,
            'pickup': {
                'address': order.pickup_address,
                'latitude': float(order.pickup_latitude) if order.pickup_latitude else None,
                'longitude': float(order.pickup_longitude) if order.pickup_longitude else None,
            } if order.pickup_latitude and order.pickup_longitude else None,
            'delivery': {
                'address': order.delivery_address,
                'latitude': float(order.delivery_latitude) if order.delivery_latitude else None,
                'longitude': float(order.delivery_longitude) if order.delivery_longitude else None,
            } if order.delivery_latitude and order.delivery_longitude else None,
            'current': {
                'latitude': float(order.current_latitude) if order.current_latitude else None,
                'longitude': float(order.current_longitude) if order.current_longitude else None,
                'last_update': order.last_location_update.isoformat() if order.last_location_update else None,
            } if order.current_latitude and order.current_longitude else None,
        }
        
        return JsonResponse(response_data)
        
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found'}, status=404)

# ============ DISPATCH RIDER VIEWS ============

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

def logout_view(request):
    """Logout user and redirect to home"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')
