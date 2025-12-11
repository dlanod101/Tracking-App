from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
# Create your models here.

USER_TYPE_CHOICES = (
    ('user', 'User'),
    ('dispatch', 'Dispatch Rider'),
)

class UserProfile(models.Model):
    """Extended user profile to differentiate user types"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='user')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    vehicle_type = models.CharField(max_length=50, blank=True, null=True)  # For dispatch riders
    license_number = models.CharField(max_length=50, blank=True, null=True)  # For dispatch riders
    is_available = models.BooleanField(default=True)  # For dispatch riders
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    total_deliveries = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_user_type_display()}"

# Auto-create profile when user is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()

STATUS = (
    ('pending', 'Pending'),
    ('dispatched', 'Dispatched'),
    ('delivered', 'Delivered'),
)

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="delivery_user")
    name = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=255, choices=STATUS, default='pending')
    
    # Location fields
    pickup_address = models.CharField(max_length=500, blank=True, null=True)
    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    
    delivery_address = models.CharField(max_length=500, blank=True, null=True)
    delivery_latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    delivery_longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    
    # Current location (updated during delivery)
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    last_location_update = models.DateTimeField(blank=True, null=True)
    
    # Dispatch rider assignment
    assigned_dispatch = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_orders")
    accepted_at = models.DateTimeField(blank=True, null=True)
    
    date_created = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Order #{self.id} - {self.name}"
    
    class Meta:
        ordering = ['-date_created']

class Delivery(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="delivery")
    dispatch = models.ForeignKey(User, on_delete=models.CASCADE, related_name="dispatch_user")
    date_created = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Delivery for Order #{self.order.id}"

class LocationUpdate(models.Model):
    """Track delivery location history for real-time tracking"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="location_updates")
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        return f"Location update for Order #{self.order.id} at {self.timestamp}"
    
    class Meta:
        ordering = ['-timestamp']