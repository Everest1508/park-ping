from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator


class CustomUser(AbstractUser):
    """Custom user model with phone number support"""
    
    # Phone number validation
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    
    # Additional fields
    phone_number = models.CharField(
        validators=[phone_regex], 
        max_length=17, 
        blank=True,
        help_text="Primary phone number for contact"
    )
    is_phone_verified = models.BooleanField(default=False)
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    
    # Subscription related fields
    current_plan = models.ForeignKey(
        'parking.SubscriptionPlan', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='subscribers'
    )
    subscription_start_date = models.DateTimeField(null=True, blank=True)
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    is_subscription_active = models.BooleanField(default=False)
    
    def __str__(self):
        return self.username
    
    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"


class UserPhoneNumber(models.Model):
    """Model to store multiple phone numbers for a user"""
    
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='phone_numbers'
    )
    phone_number = models.CharField(
        max_length=17,
        validators=[CustomUser.phone_regex]
    )
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    label = models.CharField(max_length=50, blank=True, help_text="e.g., Work, Home, Mobile")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'phone_number']
        ordering = ['-is_primary', '-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.phone_number}"
    
    def save(self, *args, **kwargs):
        # Ensure only one primary number per user
        if self.is_primary:
            UserPhoneNumber.objects.filter(user=self.user, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)