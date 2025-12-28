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
    max_masking_sessions = models.PositiveIntegerField(default=0, help_text="Maximum number of concurrent masking sessions allowed")
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
            'max_masking_sessions': self.max_masking_sessions,
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
    
    # QR Code customization settings
    qr_primary_color = models.CharField(max_length=7, default='#000000', help_text="Primary QR color")
    qr_secondary_color = models.CharField(max_length=7, default='#FFFFFF', help_text="Secondary QR color")
    qr_include_logo = models.BooleanField(default=False, help_text="Include logo in QR code")
    qr_logo_size = models.CharField(max_length=10, default='medium', choices=[('small', 'Small'), ('medium', 'Medium'), ('large', 'Large')])
    qr_size = models.CharField(max_length=10, default='medium', choices=[('small', 'Small (200x200)'), ('medium', 'Medium (300x300)'), ('large', 'Large (400x400)')])
    
    # Visibility settings
    show_phone = models.BooleanField(default=True)
    show_name = models.BooleanField(default=False)
    show_email = models.BooleanField(default=False)
    show_vehicle_details = models.BooleanField(default=True)
    
    # Emergency contact and helpline
    emergency_contact_number = models.CharField(max_length=17, blank=True, help_text="Emergency contact number to display in QR code")
    show_emergency_contact = models.BooleanField(default=False, help_text="Show emergency contact number in QR code")
    helpline_number = models.CharField(max_length=17, blank=True, help_text="Helpline number to display in QR code")
    show_helpline_number = models.BooleanField(default=False, help_text="Show helpline number in QR code")
    
    # Number masking settings
    masking_enabled = models.BooleanField(default=False, help_text="Enable number masking for this vehicle's QR code")
    
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
            # If masking is enabled, don't show the actual phone number
            if self.masking_enabled:
                info['phone'] = None  # Will be handled by masking API
                info['masking_enabled'] = True
            else:
                info['phone'] = self.contact_phone.phone_number
                info['masking_enabled'] = False
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
        # Emergency contact number
        if self.show_emergency_contact and self.emergency_contact_number:
            info['emergency_contact'] = self.emergency_contact_number
        # Helpline number - always use default ParkPing helpline
        if self.show_helpline_number:
            from django.conf import settings
            default_helpline = getattr(settings, 'PARKPING_HELPLINE_NUMBER', '+1-800-727-5746')
            if default_helpline:
                info['helpline'] = default_helpline
                info['helpline_is_default'] = True
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


class PhoneNumberMasking(models.Model):
    """Model to track phone number masking sessions"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Core fields
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='masking_sessions')
    original_phone = models.CharField(max_length=17, help_text="Original phone number being masked")
    masked_phone = models.CharField(max_length=17, help_text="Generated masked phone number")
    
    # Session management
    session_id = models.UUIDField(default=uuid.uuid4, unique=True, help_text="Unique session identifier")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="When this masking session expires")
    
    # Tracking
    call_count = models.PositiveIntegerField(default=0, help_text="Number of calls made to this masked number")
    last_called_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['vehicle', 'status']),
            models.Index(fields=['masked_phone']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.vehicle.license_plate} - {self.masked_phone} ({self.status})"
    
    def is_active(self):
        """Check if masking session is currently active"""
        from django.utils import timezone
        now = timezone.now()
        return self.status == 'active' and now <= self.expires_at
    
    def increment_call_count(self):
        """Increment call count and update last called timestamp"""
        from django.utils import timezone
        self.call_count += 1
        self.last_called_at = timezone.now()
        self.save(update_fields=['call_count', 'last_called_at'])


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
