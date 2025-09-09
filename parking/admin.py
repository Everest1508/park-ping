from django.contrib import admin
from .models import (
    SubscriptionPlan, Vehicle, QRCodeScan, 
    ParkingSession, UserSubscription
)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'plan_type', 'price', 'currency', 'billing_cycle',
        'max_vehicles', 'max_phone_numbers', 'number_masking', 'is_active'
    ]
    list_filter = ['plan_type', 'is_active', 'billing_cycle', 'number_masking']
    search_fields = ['name', 'description']
    ordering = ['price']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'plan_type', 'description', 'is_active')
        }),
        ('Pricing', {
            'fields': ('price', 'currency', 'billing_cycle')
        }),
        ('Feature Limits', {
            'fields': (
                'max_vehicles', 'max_phone_numbers', 'number_masking',
                'custom_qr_design', 'priority_support', 'analytics_dashboard'
            )
        }),
        ('Customization Options', {
            'fields': (
                'qr_color_primary', 'qr_color_secondary',
                'logo_placement', 'custom_branding'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']


class QRCodeScanInline(admin.TabularInline):
    model = QRCodeScan
    extra = 0
    readonly_fields = ['scanned_at', 'scanned_by_ip', 'scanned_by_user_agent']
    can_delete = False


class ParkingSessionInline(admin.TabularInline):
    model = ParkingSession
    extra = 0
    readonly_fields = ['start_time', 'end_time', 'status']
    can_delete = False


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = [
        'license_plate', 'user', 'vehicle_type', 'make', 'model', 'year',
        'color', 'is_qr_active', 'show_phone', 'show_name'
    ]
    list_filter = [
        'vehicle_type', 'is_qr_active', 'show_phone', 'show_name',
        'show_email', 'show_vehicle_details', 'created_at'
    ]
    search_fields = [
        'license_plate', 'user__username', 'user__email',
        'make', 'model', 'vin'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Vehicle Information', {
            'fields': (
                'user', 'vehicle_type', 'make', 'model', 'year',
                'color', 'license_plate', 'vin'
            )
        }),
        ('Contact Settings', {
            'fields': ('contact_phone',)
        }),
        ('QR Code Settings', {
            'fields': ('qr_code', 'qr_unique_id', 'is_qr_active')
        }),
        ('Visibility Settings', {
            'fields': ('show_phone', 'show_name', 'show_email', 'show_vehicle_details')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['qr_unique_id', 'created_at', 'updated_at']
    inlines = [QRCodeScanInline, ParkingSessionInline]


@admin.register(QRCodeScan)
class QRCodeScanAdmin(admin.ModelAdmin):
    list_display = [
        'vehicle', 'scanned_at', 'scanned_by_ip', 'location_lat', 'location_lng'
    ]
    list_filter = ['scanned_at', 'vehicle__vehicle_type']
    search_fields = ['vehicle__license_plate', 'vehicle__user__username']
    ordering = ['-scanned_at']
    
    fieldsets = (
        ('Scan Information', {
            'fields': ('vehicle', 'scanned_at', 'scanned_by_ip', 'scanned_by_user_agent')
        }),
        ('Location', {
            'fields': ('location_lat', 'location_lng')
        }),
    )
    
    readonly_fields = ['scanned_at']


@admin.register(ParkingSession)
class ParkingSessionAdmin(admin.ModelAdmin):
    list_display = [
        'vehicle', 'start_time', 'end_time', 'status', 'location_name'
    ]
    list_filter = ['status', 'start_time', 'vehicle__vehicle_type']
    search_fields = [
        'vehicle__license_plate', 'vehicle__user__username', 'location_name'
    ]
    ordering = ['-start_time']
    
    fieldsets = (
        ('Session Information', {
            'fields': ('vehicle', 'start_time', 'end_time', 'status')
        }),
        ('Location', {
            'fields': ('location_name', 'location_address', 'location_lat', 'location_lng')
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
    )
    
    readonly_fields = ['start_time']


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'plan', 'status', 'start_date', 'end_date',
        'amount_paid', 'payment_method'
    ]
    list_filter = ['status', 'plan', 'start_date', 'end_date']
    search_fields = ['user__username', 'user__email', 'plan__name', 'transaction_id']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Subscription Information', {
            'fields': ('user', 'plan', 'status')
        }),
        ('Billing Information', {
            'fields': ('start_date', 'end_date', 'amount_paid', 'payment_method', 'transaction_id')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
