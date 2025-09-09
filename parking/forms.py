from django import forms
from .models import Vehicle, SubscriptionPlan, ParkingSession
from accounts.models import UserPhoneNumber


class VehicleForm(forms.ModelForm):
    """Form for adding/editing vehicles"""
    
    class Meta:
        model = Vehicle
        fields = [
            'vehicle_type', 'make', 'model', 'year', 'color', 
            'license_plate', 'vin', 'contact_phone',
            'show_phone', 'show_name', 'show_email', 'show_vehicle_details'
        ]
        widgets = {
            'year': forms.NumberInput(attrs={'min': '1900', 'max': '2030'}),
            'license_plate': forms.TextInput(attrs={'placeholder': 'ABC123'}),
            'vin': forms.TextInput(attrs={'placeholder': '17-character VIN (optional)'}),
            'color': forms.TextInput(attrs={'placeholder': 'e.g., Red, Blue, White'}),
            'contact_phone': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-green-500 focus:border-green-500 text-sm'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Make VIN optional
        self.fields['vin'].required = False
        
        if self.user:
            # Filter phone numbers to only show user's phone numbers
            self.fields['contact_phone'].queryset = UserPhoneNumber.objects.filter(user=self.user)
            self.fields['contact_phone'].empty_label = "Select a phone number"
            self.fields['contact_phone'].label = "Contact Phone Number"
    
    def clean_license_plate(self):
        license_plate = self.cleaned_data['license_plate']
        if Vehicle.objects.filter(license_plate=license_plate).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise forms.ValidationError("A vehicle with this license plate already exists.")
        return license_plate
    
    def clean_vin(self):
        vin = self.cleaned_data['vin']
        if vin and Vehicle.objects.filter(vin=vin).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise forms.ValidationError("A vehicle with this VIN already exists.")
        return vin


class ParkingSessionForm(forms.ModelForm):
    """Form for creating parking sessions"""
    
    class Meta:
        model = ParkingSession
        fields = ['location_name', 'location_address', 'location_lat', 'location_lng', 'notes']
        widgets = {
            'location_name': forms.TextInput(attrs={'placeholder': 'e.g., Downtown Mall Parking'}),
            'location_address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Full address of parking location'}),
            'location_lat': forms.NumberInput(attrs={'step': 'any', 'placeholder': 'Latitude'}),
            'location_lng': forms.NumberInput(attrs={'step': 'any', 'placeholder': 'Longitude'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Additional notes about parking location'}),
        }


class QRCodeCustomizationForm(forms.Form):
    """Form for customizing QR code appearance"""
    
    COLOR_CHOICES = [
        ('#000000', 'Black'),
        ('#FFFFFF', 'White'),
        ('#FF0000', 'Red'),
        ('#00FF00', 'Green'),
        ('#0000FF', 'Blue'),
        ('#FFFF00', 'Yellow'),
        ('#FF00FF', 'Magenta'),
        ('#00FFFF', 'Cyan'),
        ('#FFA500', 'Orange'),
        ('#800080', 'Purple'),
    ]
    
    primary_color = forms.ChoiceField(
        choices=COLOR_CHOICES,
        initial='#000000',
        label='Primary Color',
        help_text='Main color for QR code'
    )
    
    secondary_color = forms.ChoiceField(
        choices=COLOR_CHOICES,
        initial='#FFFFFF',
        label='Secondary Color',
        help_text='Background color for QR code'
    )
    
    include_logo = forms.BooleanField(
        required=False,
        label='Include Logo',
        help_text='Add your logo to the center of QR code'
    )
    
    logo_size = forms.ChoiceField(
        choices=[
            ('small', 'Small'),
            ('medium', 'Medium'),
            ('large', 'Large'),
        ],
        initial='medium',
        required=False,
        label='Logo Size'
    )
    
    qr_size = forms.ChoiceField(
        choices=[
            ('small', 'Small (200x200)'),
            ('medium', 'Medium (300x300)'),
            ('large', 'Large (400x400)'),
        ],
        initial='medium',
        label='QR Code Size'
    )


class SubscriptionPlanSelectionForm(forms.Form):
    """Form for selecting subscription plans"""
    
    plan = forms.ModelChoiceField(
        queryset=SubscriptionPlan.objects.filter(is_active=True),
        empty_label=None,
        widget=forms.RadioSelect,
        label='Select Plan'
    )
    
    billing_cycle = forms.ChoiceField(
        choices=[
            ('monthly', 'Monthly'),
            ('yearly', 'Yearly (Save 20%)'),
        ],
        initial='monthly',
        widget=forms.RadioSelect,
        label='Billing Cycle'
    )
    
    auto_renew = forms.BooleanField(
        required=False,
        initial=True,
        label='Auto-renew subscription',
        help_text='Automatically renew your subscription when it expires'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customize the plan choices to show pricing
        self.fields['plan'].choices = [
            (plan.id, f"{plan.name} - ${plan.price}/{plan.billing_cycle}")
            for plan in SubscriptionPlan.objects.filter(is_active=True)
        ]


class VehicleSearchForm(forms.Form):
    """Form for searching vehicles by QR code"""
    
    search_query = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Scan QR code or enter license plate',
            'class': 'form-control'
        }),
        label='Search Vehicle'
    )
    
    def clean_search_query(self):
        query = self.cleaned_data['search_query'].strip()
        if not query:
            raise forms.ValidationError("Please enter a search query.")
        return query


class ContactOwnerForm(forms.Form):
    """Form for contacting vehicle owner"""
    
    CONTACT_REASONS = [
        ('blocking', 'Vehicle is blocking my car'),
        ('damage', 'Vehicle appears to be damaged'),
        ('emergency', 'Emergency situation'),
        ('other', 'Other reason'),
    ]
    
    reason = forms.ChoiceField(
        choices=CONTACT_REASONS,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Reason for Contact'
    )
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Please describe the situation...',
            'class': 'form-control'
        }),
        label='Message (Optional)',
        required=False
    )
    
    contact_method = forms.ChoiceField(
        choices=[
            ('call', 'Call Owner'),
            ('sms', 'Send SMS'),
        ],
        initial='call',
        widget=forms.RadioSelect,
        label='Preferred Contact Method'
    )