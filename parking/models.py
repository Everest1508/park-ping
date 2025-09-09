from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import CustomUser
import uuid


class SubscriptionPlan(models.Model):
    """Model for subscription plans"""
    
    PLAN_TYPES = [
        ('free', 'Free'),
        ('basic', 'Basic'),
        ('pro', 'Professional'),
        ('enterprise', 'Enterprise'),
    ]
    
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES, unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, default='USD')
    billing_cycle = models.CharField(max_length=20, default='monthly')
    
    # Feature limits
    max_vehicles = models.PositiveIntegerField(default=1)
    max_phone_numbers = models.PositiveIntegerField(default=1)
    number_masking = models.BooleanField(default=False)
    custom_qr_design = models.BooleanField(default=False)
    priority_support = models.BooleanField(default=False)
    analytics_dashboard = models.BooleanField(default=False)
    
    # Customization options
    qr_color_primary = models.CharField(max_length=7, default='#000000', help_text="Primary QR color")
    qr_color_secondary = models.CharField(max_length=7, default='#FFFFFF', help_text="Secondary QR color")
    logo_placement = models.BooleanField(default=False)
    custom_branding = models.BooleanField(default=False)
    
    # Plan status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['price']
    
    def __str__(self):
        return f"{self.name} - {self.plan_type}"
    
    def get_features(self):
        """Return a dictionary of plan features"""
        return {
            'max_vehicles': self.max_vehicles,
            'max_phone_numbers': self.max_phone_numbers,
            'number_masking': self.number_masking,
            'custom_qr_design': self.custom_qr_design,
            'priority_support': self.priority_support,
            'analytics_dashboard': self.analytics_dashboard,
        }


class Vehicle(models.Model):
    """Model for user vehicles"""
    
    VEHICLE_TYPES = [
        ('car', 'Car'),
        ('motorcycle', 'Motorcycle'),
        ('truck', 'Truck'),
        ('van', 'Van'),
        ('suv', 'SUV'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='vehicles')
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES, default='car')
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.PositiveIntegerField()
    color = models.CharField(max_length=50)
    license_plate = models.CharField(max_length=20, unique=True)
    vin = models.CharField(max_length=17, blank=True, help_text="Vehicle Identification Number")
    
    # Contact information
    contact_phone = models.ForeignKey(
        'accounts.UserPhoneNumber',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vehicle_contacts'
    )
    
    # QR Code settings
    qr_code = models.ImageField(upload_to='qr_codes/', null=True, blank=True)
    qr_unique_id = models.UUIDField(default=uuid.uuid4, unique=True)
    is_qr_active = models.BooleanField(default=True)
    
    # Visibility settings
    show_phone = models.BooleanField(default=True)
    show_name = models.BooleanField(default=False)
    show_email = models.BooleanField(default=False)
    show_vehicle_details = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.year} {self.make} {self.model} - {self.license_plate}"
    
    def get_contact_info(self):
        """Return contact information based on visibility settings"""
        info = {}
        if self.show_phone and self.contact_phone:
            info['phone'] = self.contact_phone.phone_number
        if self.show_name:
            info['name'] = self.user.get_full_name() or self.user.username
        if self.show_email:
            info['email'] = self.user.email
        if self.show_vehicle_details:
            info['vehicle'] = {
                'make': self.make,
                'model': self.model,
                'year': self.year,
                'color': self.color,
                'license_plate': self.license_plate
            }
        return info


class QRCodeScan(models.Model):
    """Model to track QR code scans"""
    
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='scans')
    scanned_by_ip = models.GenericIPAddressField(null=True, blank=True)
    scanned_by_user_agent = models.TextField(blank=True)
    scanned_at = models.DateTimeField(auto_now_add=True)
    location_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    class Meta:
        ordering = ['-scanned_at']
    
    def __str__(self):
        return f"Scan of {self.vehicle} at {self.scanned_at}"


class ParkingSession(models.Model):
    """Model to track parking sessions"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='parking_sessions')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Location information
    location_name = models.CharField(max_length=200, blank=True)
    location_address = models.TextField(blank=True)
    location_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-start_time']
    
    def __str__(self):
        return f"{self.vehicle} - {self.start_time} to {self.end_time or 'Ongoing'}"
    
    def duration(self):
        """Calculate parking duration"""
        if self.end_time:
            return self.end_time - self.start_time
        return None


class UserSubscription(models.Model):
    """Model to track user subscription history"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Billing information
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.plan.name} ({self.status})"
    
    def is_active(self):
        """Check if subscription is currently active"""
        from django.utils import timezone
        now = timezone.now()
        return self.status == 'active' and self.start_date <= now <= self.end_date
