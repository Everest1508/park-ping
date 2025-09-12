from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.validators import RegexValidator
from .models import CustomUser, UserPhoneNumber


class CustomUserCreationForm(UserCreationForm):
    """Form for creating new users"""
    
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    
    phone_number = forms.CharField(
        validators=[phone_regex],
        max_length=17,
        required=False,
        help_text="Primary phone number for contact",
        widget=forms.TextInput(attrs={'class': 'mt-1 block w-full px-4 py-2 rounded-lg text-gray-900 focus:outline-none', 'placeholder': '+1234567890'})
    )
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'mt-1 block w-full px-4 py-2 rounded-lg text-gray-900 focus:outline-none'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add CSS classes to all form fields to match login form exactly
        for field_name, field in self.fields.items():
            if field_name not in ['phone_number', 'date_of_birth']:  # Skip fields we already styled
                field.widget.attrs.update({'class': 'mt-1 block w-full px-4 py-2 rounded-lg text-gray-900 focus:outline-none'})
            
            # Add placeholders
            if field_name == 'first_name':
                field.widget.attrs['placeholder'] = 'First name'
            elif field_name == 'last_name':
                field.widget.attrs['placeholder'] = 'Last name'
            elif field_name == 'username':
                field.widget.attrs['placeholder'] = 'Choose a username'
            elif field_name == 'email':
                field.widget.attrs['placeholder'] = 'Enter your email'
            elif field_name == 'password1':
                field.widget.attrs['placeholder'] = 'Password'
            elif field_name == 'password2':
                field.widget.attrs['placeholder'] = 'Confirm password'
    
    def add_error_class(self, field_name):
        """Add error class to field widget"""
        if field_name in self.fields:
            current_class = self.fields[field_name].widget.attrs.get('class', '')
            if 'border-red-500' not in current_class:
                self.fields[field_name].widget.attrs['class'] = f"{current_class} border-red-500".strip()
    
    def clean(self):
        cleaned_data = super().clean()
        # Add error class to fields with errors
        for field_name, errors in self.errors.items():
            if errors:
                self.add_error_class(field_name)
        return cleaned_data
    
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = UserCreationForm.Meta.fields + (
            'email', 'first_name', 'last_name', 'phone_number', 'date_of_birth'
        )
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.phone_number = self.cleaned_data.get('phone_number')
        user.date_of_birth = self.cleaned_data.get('date_of_birth')
        
        if commit:
            user.save()
            # Create primary phone number if provided
            if user.phone_number:
                UserPhoneNumber.objects.create(
                    user=user,
                    phone_number=user.phone_number,
                    is_primary=True,
                    is_verified=False,
                    label='Primary'
                )
        return user


class CustomUserChangeForm(UserChangeForm):
    """Form for updating existing users"""
    
    class Meta(UserChangeForm.Meta):
        model = CustomUser
        fields = UserChangeForm.Meta.fields


class CustomUserProfileForm(forms.ModelForm):
    """Form for updating user profile information"""
    
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'username', 'email', 'phone_number', 'date_of_birth', 'profile_picture']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'first_name': forms.TextInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-green-500 focus:border-green-500 text-sm'}),
            'last_name': forms.TextInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-green-500 focus:border-green-500 text-sm'}),
            'username': forms.TextInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-green-500 focus:border-green-500 text-sm'}),
            'email': forms.EmailInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-green-500 focus:border-green-500 text-sm'}),
            'phone_number': forms.TextInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-green-500 focus:border-green-500 text-sm'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-green-500 focus:border-green-500 text-sm'}),
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'hidden', 'accept': 'image/*'}),
        }


class UserPhoneNumberForm(forms.ModelForm):
    """Form for adding/editing phone numbers"""
    
    class Meta:
        model = UserPhoneNumber
        fields = ['phone_number', 'label', 'is_primary']
        widgets = {
            'phone_number': forms.TextInput(attrs={'placeholder': '+1234567890'}),
            'label': forms.TextInput(attrs={'placeholder': 'e.g., Work, Home, Mobile'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # Don't allow changing primary status if this is the only phone number
            existing_numbers = UserPhoneNumber.objects.filter(user=self.user)
            if existing_numbers.count() <= 1:
                self.fields['is_primary'].widget.attrs['disabled'] = True
                self.fields['is_primary'].help_text = "Cannot remove primary status from the only phone number"
    
    def clean(self):
        cleaned_data = super().clean()
        phone_number = cleaned_data.get('phone_number')
        is_primary = cleaned_data.get('is_primary')
        
        if phone_number and self.user:
            # Check if phone number already exists for this user
            existing = UserPhoneNumber.objects.filter(
                user=self.user, 
                phone_number=phone_number
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing.exists():
                raise forms.ValidationError("This phone number is already registered for your account.")
        
        return cleaned_data


class PhoneNumberVerificationForm(forms.Form):
    """Form for phone number verification"""
    
    verification_code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter 6-digit code',
            'maxlength': '6',
            'pattern': '[0-9]{6}'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.phone_number = kwargs.pop('phone_number', None)
        super().__init__(*args, **kwargs)
    
    def clean_verification_code(self):
        code = self.cleaned_data['verification_code']
        if not code.isdigit() or len(code) != 6:
            raise forms.ValidationError("Please enter a valid 6-digit verification code.")
        return code