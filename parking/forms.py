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
            'show_phone', 'show_name', 'show_email', 'show_vehicle_details',
            'emergency_contact_number', 'show_emergency_contact',
            'show_helpline_number',
            'masking_enabled'
        ]
        widgets = {
            'year': forms.NumberInput(attrs={'min': '1900', 'max': '2030'}),
            'license_plate': forms.TextInput(attrs={'placeholder': 'ABC123'}),
            'vin': forms.TextInput(attrs={'placeholder': '17-character VIN (optional)'}),
            'color': forms.TextInput(attrs={'placeholder': 'e.g., Red, Blue, White'}),
            'contact_phone': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-green-500 focus:border-green-500 text-sm'}),
            'emergency_contact_number': forms.TextInput(attrs={'placeholder': 'e.g., +1234567890', 'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-green-500 focus:border-green-500 text-sm'}),
            'show_emergency_contact': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-green-600 focus:ring-green-500 border-gray-300 rounded'}),
            'show_helpline_number': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-green-600 focus:ring-green-500 border-gray-300 rounded'}),
            'masking_enabled': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-green-600 focus:ring-green-500 border-gray-300 rounded'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Make VIN optional
        self.fields['vin'].required = False
        
        # Make emergency contact optional
        self.fields['emergency_contact_number'].required = False
        self.fields['emergency_contact_number'].help_text = "Optional: Add an emergency contact number to display in QR code"
        
        # Update helpline help text to indicate it's always ParkPing helpline
        from django.conf import settings
        default_helpline = getattr(settings, 'PARKPING_HELPLINE_NUMBER', '+1-800-727-5746')
        self.fields['show_helpline_number'].help_text = f"Show ParkPing helpline number ({default_helpline}) in QR code"
        
        if self.user:
            # Filter phone numbers to only show user's phone numbers
            phone_numbers = UserPhoneNumber.objects.filter(user=self.user)
            self.fields['contact_phone'].queryset = phone_numbers
            
            if phone_numbers.exists():
                self.fields['contact_phone'].empty_label = "Select a phone number"
                self.fields['contact_phone'].label = "Contact Phone Number"
            else:
                self.fields['contact_phone'].empty_label = "No phone numbers available - Add one first"
                self.fields['contact_phone'].label = "Contact Phone Number (Optional)"
                self.fields['contact_phone'].required = False
                self.fields['contact_phone'].help_text = "Add a phone number in your profile to enable contact features"
            
            # Check if user's plan supports masking
            user_plan = self.user.current_plan
            if not user_plan or not user_plan.number_masking:
                self.fields['masking_enabled'].widget.attrs['disabled'] = True
                self.fields['masking_enabled'].widget.attrs['class'] += ' opacity-50 cursor-not-allowed'
                self.fields['masking_enabled'].help_text = "Number masking requires a premium plan"
            else:
                self.fields['masking_enabled'].help_text = f"Enable number masking for this vehicle (Plan allows {user_plan.max_masking_sessions} concurrent sessions)"
    
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
    
    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    billing_cycle = forms.ChoiceField(
        choices=BILLING_CYCLE_CHOICES,
        initial='monthly',
        widget=forms.RadioSelect,
        label='Billing Cycle',
        required=False  # Free plans don't need billing cycle
    )
    
    agree_terms = forms.BooleanField(
        required=True,
        label='I agree to the Terms of Service and Privacy Policy'
    )
    
    auto_renew = forms.BooleanField(
        required=False,
        initial=True,
        label='Auto-renew subscription',
        help_text='Automatically renew your subscription when it expires'
    )
    


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