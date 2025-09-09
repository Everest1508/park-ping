from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, UserPhoneNumber


class UserPhoneNumberInline(admin.TabularInline):
    model = UserPhoneNumber
    extra = 1
    fields = ['phone_number', 'is_primary', 'is_verified', 'label']


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'email', 'phone_number', 'current_plan', 'is_subscription_active', 'is_active']
    list_filter = ['is_subscription_active', 'current_plan', 'is_active', 'is_staff', 'date_joined']
    search_fields = ['username', 'email', 'phone_number', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Profile Information', {
            'fields': ('phone_number', 'is_phone_verified', 'date_of_birth', 'profile_picture')
        }),
        ('Subscription Information', {
            'fields': ('current_plan', 'subscription_start_date', 'subscription_end_date', 'is_subscription_active')
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Profile Information', {
            'fields': ('phone_number', 'date_of_birth')
        }),
    )
    
    inlines = [UserPhoneNumberInline]


@admin.register(UserPhoneNumber)
class UserPhoneNumberAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'is_primary', 'is_verified', 'label', 'created_at']
    list_filter = ['is_primary', 'is_verified', 'label', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone_number']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Phone Number Information', {
            'fields': ('user', 'phone_number', 'is_primary', 'is_verified', 'label')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at']
