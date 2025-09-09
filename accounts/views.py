from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json

from .forms import (
    CustomUserCreationForm, CustomUserProfileForm, 
    UserPhoneNumberForm, PhoneNumberVerificationForm
)
from .models import CustomUser, UserPhoneNumber


class SignUpView(CreateView):
    """View for user registration"""
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('accounts:dashboard')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # Log the user in after successful registration
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password1')
        user = authenticate(username=username, password=password)
        if user:
            login(self.request, user)
            messages.success(self.request, 'Account created successfully! Welcome to ParkPing!')
        return response


class CustomLoginView(LoginView):
    """Custom login view"""
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('accounts:dashboard')


@login_required
def profile_view(request):
    """View for user profile"""
    if request.method == 'POST':
        form = CustomUserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = CustomUserProfileForm(instance=request.user)
    
    context = {
        'form': form,
        'user': request.user,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def phone_numbers_view(request):
    """View for managing phone numbers"""
    phone_numbers = UserPhoneNumber.objects.filter(user=request.user)
    
    if request.method == 'POST':
        form = UserPhoneNumberForm(request.POST, user=request.user)
        if form.is_valid():
            phone_number = form.save(commit=False)
            phone_number.user = request.user
            phone_number.save()
            messages.success(request, 'Phone number added successfully!')
            return redirect('accounts:phone_numbers')
    else:
        form = UserPhoneNumberForm(user=request.user)
    
    context = {
        'form': form,
        'phone_numbers': phone_numbers,
    }
    return render(request, 'accounts/phone_numbers.html', context)


@login_required
def edit_phone_number(request, pk):
    """View for editing phone numbers"""
    phone_number = get_object_or_404(UserPhoneNumber, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = UserPhoneNumberForm(request.POST, instance=phone_number, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Phone number updated successfully!')
            return redirect('accounts:phone_numbers')
    else:
        form = UserPhoneNumberForm(instance=phone_number, user=request.user)
    
    context = {
        'form': form,
        'phone_number': phone_number,
    }
    return render(request, 'accounts/edit_phone_number.html', context)


@login_required
@require_POST
def delete_phone_number(request, pk):
    """View for deleting phone numbers"""
    phone_number = get_object_or_404(UserPhoneNumber, pk=pk, user=request.user)
    
    # Don't allow deletion if it's the only phone number
    if UserPhoneNumber.objects.filter(user=request.user).count() <= 1:
        messages.error(request, 'Cannot delete the only phone number. Please add another one first.')
        return redirect('accounts:phone_numbers')
    
    phone_number.delete()
    messages.success(request, 'Phone number deleted successfully!')
    return redirect('accounts:phone_numbers')


@login_required
@require_POST
def set_primary_phone(request, pk):
    """View for setting primary phone number"""
    phone_number = get_object_or_404(UserPhoneNumber, pk=pk, user=request.user)
    
    # Set this as primary
    UserPhoneNumber.objects.filter(user=request.user, is_primary=True).update(is_primary=False)
    phone_number.is_primary = True
    phone_number.save()
    
    messages.success(request, f'{phone_number.phone_number} is now your primary phone number!')
    return redirect('accounts:phone_numbers')


@login_required
def verify_phone_number(request, pk):
    """View for phone number verification"""
    phone_number = get_object_or_404(UserPhoneNumber, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = PhoneNumberVerificationForm(request.POST, phone_number=phone_number.phone_number)
        if form.is_valid():
            # In a real application, you would verify the code here
            # For now, we'll just mark it as verified
            phone_number.is_verified = True
            phone_number.save()
            
            # Update user's primary phone verification status if this is the primary
            if phone_number.is_primary:
                request.user.is_phone_verified = True
                request.user.save()
            
            messages.success(request, 'Phone number verified successfully!')
            return redirect('accounts:phone_numbers')
    else:
        form = PhoneNumberVerificationForm(phone_number=phone_number.phone_number)
    
    context = {
        'form': form,
        'phone_number': phone_number,
    }
    return render(request, 'accounts/verify_phone.html', context)




@csrf_exempt
@require_POST
def send_verification_code(request):
    """API endpoint for sending verification codes"""
    try:
        data = json.loads(request.body)
        phone_number = data.get('phone_number')
        
        if not phone_number:
            return JsonResponse({'error': 'Phone number is required'}, status=400)
        
        # In a real application, you would integrate with SMS service here
        # For now, we'll just return success
        return JsonResponse({
            'message': 'Verification code sent successfully',
            'phone_number': phone_number
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def dashboard_view(request):
    """Dashboard view for authenticated users"""
    user = request.user
    vehicles = user.vehicles.all()
    phone_numbers = user.phone_numbers.all()
    
    # Get subscription info
    subscription = None
    if user.current_plan:
        subscription = {
            'plan': user.current_plan,
            'is_active': user.is_subscription_active,
            'start_date': user.subscription_start_date,
            'end_date': user.subscription_end_date,
        }
    
    context = {
        'user': user,
        'vehicles': vehicles,
        'phone_numbers': phone_numbers,
        'subscription': subscription,
    }
    return render(request, 'accounts/dashboard.html', context)


@login_required
def change_password_view(request):
    """View for changing user password"""
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        # Validate old password
        if not request.user.check_password(old_password):
            messages.error(request, 'Your old password was entered incorrectly. Please enter it again.')
            return redirect('accounts:profile')
        
        # Validate new passwords match
        if new_password1 != new_password2:
            messages.error(request, 'The two password fields didn\'t match.')
            return redirect('accounts:profile')
        
        # Validate password strength
        if len(new_password1) < 8:
            messages.error(request, 'This password is too short. It must contain at least 8 characters.')
            return redirect('accounts:profile')
        
        # Set new password
        request.user.set_password(new_password1)
        request.user.save()
        messages.success(request, 'Your password was successfully updated!')
        return redirect('accounts:profile')
    
    return redirect('accounts:profile')
