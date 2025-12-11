# DISPATCH RIDER SYSTEM - IMPLEMENTATION GUIDE

## Overview

This guide explains how to integrate the dispatch rider system into your TrackFlow application.

## Step 1: Database Migrations

**IMPORTANT**: Run these migrations first:

```bash
python manage.py makemigrations
python manage.py migrate
```

This will create:

- `UserProfile` table
- Add `assigned_dispatch` and `accepted_at` fields to `Order` table

## Step 2: Update views.py

### Option A: Merge the dispatch_views.py content into your main/views.py

Open `main/dispatch_views.py` and copy the following functions to `main/views.py`:

1. **Replace the existing `register_view` function** (around line 34-61) with the updated version from dispatch_views.py
2. **Replace the existing `login_view` function** (around line 16-32) with the updated version from dispatch_views.py
3. **Add these new functions** at the end of views.py:
   - `dispatch_dashboard`
   - `accept_order`
   - `dispatch_tracking`
   - `complete_delivery`

### Option B: Import dispatch views

Add to the top of `main/views.py`:

```python
from .dispatch_views import (
    dispatch_dashboard, accept_order, 
    dispatch_tracking, complete_delivery
)
```

And update the existing `register_view` and `login_view` with the versions from `dispatch_views.py`.

## Step 3: Update URLs (main/urls.py)

Add these URL patterns:

```python
from django.urls import path
from .views import (
    index, login_view, register_view, dashboard, logout_view,
    create_order, track_order, update_location, get_order_location,
    # Add dispatch views
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
```

## Step 4: Update register.html Template

Add user type selection and conditional fields for dispatch riders:

```html
{% extends 'base.html' %}

{% block title %}Register - TrackFlow{% endblock %}

{% block content %}
<!-- Add after the email field -->

<!-- User Type Selection -->
<div class="form-group">
    <label class="form-label">Register As *</label>
    <div style="display: flex; gap: 1rem; margin-top: 0.5rem;">
        <label style="flex: 1; cursor: pointer;">
            <input type="radio" name="user_type" value="user" checked onchange="toggleDispatchFields()">
            <span style="margin-left: 0.5rem;">Customer</span>
        </label>
        <label style="flex: 1; cursor: pointer;">
            <input type="radio" name="user_type" value="dispatch" onchange="toggleDispatchFields()">
            <span style="margin-left: 0.5rem;">Dispatch Rider</span>
        </label>
    </div>
</div>

<!-- Dispatch-specific fields (hidden by default) -->
<div id="dispatch-fields" style="display: none;">
    <div class="form-group">
        <label for="phone_number" class="form-label">Phone Number *</label>
        <input type="tel" id="phone_number" name="phone_number" class="form-input" placeholder="+234 XXX XXX XXXX">
    </div>
    
    <div class="form-group">
        <label for="vehicle_type" class="form-label">Vehicle Type *</label>
        <select id="vehicle_type" name="vehicle_type" class="form-input">
            <option value="">Select vehicle type</option>
            <option value="motorcycle">Motorcycle</option>
            <option value="bicycle">Bicycle</option>
            <option value="car">Car</option>
            <option value="van">Van</option>
        </select>
    </div>
    
    <div class="form-group">
        <label for="license_number" class="form-label">License Number (Optional)</label>
        <input type="text" id="license_number" name="license_number" class="form-input" placeholder="DL123456">
    </div>
</div>

<!-- Add this JavaScript at the end -->
<script>
function toggleDispatchFields() {
    const userType = document.querySelector('input[name="user_type"]:checked').value;
    const dispatchFields = document.getElementById('dispatch-fields');
    
    if (userType === 'dispatch') {
        dispatchFields.style.display = 'block';
        // Make dispatch fields required
        document.getElementById('phone_number').required = true;
        document.getElementById('vehicle_type').required = true;
    } else {
        dispatchFields.style.display = 'none';
        // Make dispatch fields optional
        document.getElementById('phone_number').required = false;
        document.getElementById('vehicle_type').required = false;
    }
}
</script>
{% endblock %}
```

## Step 5: Create Dispatch Dashboard Template (dispatch_dashboard.html)

Create `main/templates/dispatch_dashboard.html`:

**KEY FEATURES**:

- Show dispatch rider statistics (total deliveries, rating, active orders)
- List of available orders to accept
- List of assigned/active orders
- Quick actions (toggle availability, view profile)

See DISPATCH_DASHBOARD_TEMPLATE.md for the complete HTML template.

## Step 6: Create Dispatch Tracking Template (dispatch_tracking.html)

Create `main/templates/dispatch_tracking.html`:

**KEY FEATURES**:

- Interactive map showing route (pickup → current → delivery)
- GPS tracking button to share location
- Location updates sent every 30 seconds
- "Complete Delivery" button
- Order details panel

See DISPATCH_TRACKING_TEMPLATE.md for the complete HTML template.

## Step 7: Update the Update Location API

The `update_location` view in views.py should already work, but ensure it's accessible for dispatch riders to send their GPS coordinates.

## How It Works

### User Flow

**Registration**:

1. User chooses "Customer" or "Dispatch Rider"
2. If Dispatch Rider, additional fields appear (phone, vehicle, license)
3. User registers and is redirected to appropriate dashboard

**Login**:

1. User logs in
2. System checks user type
3. Redirects to dispatch dashboard or customer dashboard

**Dispatch Rider Workflow**:

1. Login → Dispatch Dashboard
2. See available orders
3. Click "Accept Order"
4. Redirected to tracking interface
5. Share GPS location (auto-updates every 30s)
6. Customer sees rider's location in real-time
7. Mark as "Delivered" when complete

**Customer Tracking**:

1. Customer creates order
2. Dispatch rider accepts
3. Customer tracks via "Track" button
4. Map shows:
   - Pickup location (green)
   - Delivery location (red)
   - Rider's current location (blue) - updates live!

### Technical Details

**Location Sharing**:

- Dispatch tracking page uses HTML5 Geolocation API
- Sends coordinates to `/api/update-location/<order_id>/` every 30 seconds
- Updates `Order.current_latitude/longitude`
- Creates `LocationUpdate` record for history

**Real-time Updates**:

- Customer tracking page polls `/api/get-location/<order_id>/` every 10 seconds
- Map marker moves to show rider's current position
- Route line updates dynamically

## Testing Checklist

### Prerequisites

- [ ] Run migrations
- [ ] Update views.py with dispatch functions
- [ ] Update urls.py with dispatch routes
- [ ] Update register.html with user type selection
- [ ] Create dispatch_dashboard.html
- [ ] Create dispatch_tracking.html

### Test Flow

- [ ] Register as customer - redirects to user dashboard
- [ ] Register as dispatch rider - redirects to dispatch dashboard
- [ ] Login as dispatch rider - sees dispatch dashboard
- [ ] Create order as customer
- [ ] Accept order as dispatch rider
- [ ] Open tracking interface as dispatch rider
- [ ] Share GPS location - see it update on customer's tracking page
- [ ] Complete delivery - order status updates to "Delivered"
- [ ] Check dispatch rider stats updated

## Security Notes

**Important for Production**:

1. Add permission checks in all dispatch views
2. Validate that dispatch riders can only access their own orders
3. Add rate limiting on location update API
4. Use CSRF tokens properly (remove `@csrf_exempt` in production)
5. Validate GPS coordinates (lat: -90 to 90, lng: -180 to 180)

## Next Steps

After implementation:

1. Add dispatch rider approval system (admin approval before accepting orders)
2. Add rating system (customers rate dispatch riders)
3. Add earnings tracking for dispatch riders
4. Add push notifications for new orders
5. Create mobile app for dispatch riders
6. Add route optimization
7. Add multi-language support

## Troubleshooting

**Issue**: "No module named 'dispatch_views'"
**Solution**: Either merge dispatch_views.py into views.py or use proper import

**Issue**: Profile does not exist
**Solution**: Run migrations, check signal handlers in models.py

**Issue**: Location not updating
**Solution**: Check browser permissions for geolocation, verify API endpoint works

**Issue**: Dispatch rider can't access dashboard
**Solution**: Check user_type in UserProfile is set to 'dispatch'

## File Summary

**Modified Files**:

- `main/models.py` ✅ (UserProfile, Order updates)
- `main/views.py` (add dispatch functions)
- `main/urls.py` (add dispatch routes)
- `main/templates/register.html` (add user type selection)

**New Files to Create**:

- `main/templates/dispatch_dashboard.html`
- `main/templates/dispatch_tracking.html`

**Helper File** (can delete after merging):

- `main/dispatch_views.py`

---

**Status**: Configuration Required
**Complexity**: High
**Estimated Time**: 2-3 hours for full integration
