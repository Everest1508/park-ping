from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Q
import qrcode
from io import BytesIO
import json

from .models import (
    Vehicle, SubscriptionPlan, ParkingSession, 
    QRCodeScan, UserSubscription
)
from .forms import (
    VehicleForm, ParkingSessionForm, QRCodeCustomizationForm,
    SubscriptionPlanSelectionForm, VehicleSearchForm, ContactOwnerForm
)
from accounts.models import CustomUser, UserPhoneNumber


@login_required
def vehicle_list(request):
    """View for listing user's vehicles"""
    vehicles = Vehicle.objects.filter(user=request.user)
    
    # Check subscription limits
    user_plan = request.user.current_plan
    max_vehicles = user_plan.max_vehicles if user_plan else 1
    
    # Calculate stats
    active_qr_count = vehicles.filter(is_qr_active=True).count()
    recent_scans = QRCodeScan.objects.filter(
        vehicle__user=request.user,
        scanned_at__gte=timezone.now() - timezone.timedelta(days=7)
    ).count()
    
    context = {
        'vehicles': vehicles,
        'max_vehicles': max_vehicles,
        'can_add_vehicle': vehicles.count() < max_vehicles,
        'active_qr_count': active_qr_count,
        'recent_scans': recent_scans,
    }
    return render(request, 'parking/vehicle_list.html', context)


@login_required
def qr_codes(request):
    """View for managing QR codes"""
    vehicles = Vehicle.objects.filter(user=request.user)
    
    # Calculate stats
    active_qr_count = vehicles.filter(is_qr_active=True).count()
    recent_scans = QRCodeScan.objects.filter(
        vehicle__user=request.user,
        scanned_at__gte=timezone.now() - timezone.timedelta(days=7)
    ).count()
    
    context = {
        'vehicles': vehicles,
        'active_qr_count': active_qr_count,
        'recent_scans': recent_scans,
    }
    return render(request, 'parking/qr_codes.html', context)


@login_required
def add_vehicle(request):
    """View for adding new vehicles"""
    # Check subscription limits
    user_plan = request.user.current_plan
    max_vehicles = user_plan.max_vehicles if user_plan else 1
    current_count = Vehicle.objects.filter(user=request.user).count()
    
    if current_count >= max_vehicles:
        messages.error(request, f'You have reached the maximum number of vehicles ({max_vehicles}) for your plan.')
        return redirect('parking:vehicle_list')
    
    if request.method == 'POST':
        form = VehicleForm(request.POST, user=request.user)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.user = request.user
            vehicle.save()
            
            # Generate QR code
            generate_qr_code(vehicle, request)
            
            messages.success(request, 'Vehicle added successfully!')
            return redirect('parking:vehicle_list')
    else:
        form = VehicleForm(user=request.user)
    
    # Get user's phone numbers
    phone_numbers = UserPhoneNumber.objects.filter(user=request.user)
    
    # Calculate stats
    vehicles = Vehicle.objects.filter(user=request.user)
    active_qr_count = vehicles.filter(is_qr_active=True).count()
    
    context = {
        'form': form,
        'max_vehicles': max_vehicles,
        'current_count': current_count,
        'phone_numbers': phone_numbers,
        'vehicles': vehicles,
        'active_qr_count': active_qr_count,
    }
    return render(request, 'parking/add_vehicle.html', context)


@login_required
def edit_vehicle(request, pk):
    """View for editing vehicles"""
    vehicle = get_object_or_404(Vehicle, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = VehicleForm(request.POST, instance=vehicle, user=request.user)
        if form.is_valid():
            form.save()
        messages.success(request, 'Vehicle updated successfully!')
        return redirect('parking:vehicle_list')
    else:
        form = VehicleForm(instance=vehicle, user=request.user)
    
    context = {
        'form': form,
        'vehicle': vehicle,
    }
    return render(request, 'parking/edit_vehicle.html', context)


@login_required
@require_POST
def delete_vehicle(request, pk):
    """View for deleting vehicles"""
    vehicle = get_object_or_404(Vehicle, pk=pk, user=request.user)
    vehicle.delete()
    messages.success(request, 'Vehicle deleted successfully!')
    return redirect('parking:vehicle_list')


@login_required
def vehicle_detail(request, pk):
    """View for vehicle details and QR code"""
    vehicle = get_object_or_404(Vehicle, pk=pk, user=request.user)
    
    # Get QR code scans
    scans = QRCodeScan.objects.filter(vehicle=vehicle).order_by('-scanned_at')[:10]
    
    # Get active parking sessions
    active_sessions = ParkingSession.objects.filter(
        vehicle=vehicle, 
        status='active'
    ).order_by('-start_time')
    
    context = {
        'vehicle': vehicle,
        'scans': scans,
        'active_sessions': active_sessions,
    }
    return render(request, 'parking/vehicle_detail.html', context)


@login_required
@require_POST
def regenerate_qr_code(request, pk):
    """Regenerate QR code for a vehicle"""
    vehicle = get_object_or_404(Vehicle, pk=pk, user=request.user)
    
    # Regenerate QR code
    generate_qr_code(vehicle, request)
    
    messages.success(request, 'QR code regenerated successfully!')
    return redirect('parking:vehicle_detail', pk=pk)


@login_required
@require_POST
def toggle_qr_code(request, pk):
    """Toggle QR code active status for a vehicle"""
    vehicle = get_object_or_404(Vehicle, pk=pk, user=request.user)
    
    # Toggle QR code status
    vehicle.is_qr_active = not vehicle.is_qr_active
    vehicle.save()
    
    status = 'activated' if vehicle.is_qr_active else 'deactivated'
    messages.success(request, f'QR code {status} successfully!')
    return redirect('parking:vehicle_detail', pk=pk)


def generate_qr_code(vehicle, request=None):
    """Generate QR code for a vehicle"""
    from django.urls import reverse
    from django.conf import settings
    
    # Create QR code URL that leads to the contact page
    qr_url = reverse('parking:scan_qr_code', kwargs={'qr_id': vehicle.qr_unique_id})
    
    # Try to build a full URL with domain
    if request:
        # Use the request to build the full URL
        qr_data = request.build_absolute_uri(qr_url)
    elif hasattr(settings, 'SITE_URL') and settings.SITE_URL:
        # Use configured site URL
        qr_data = f"{settings.SITE_URL.rstrip('/')}{qr_url}"
    else:
        # Fall back to relative URL for development
        # In production, you should set SITE_URL in settings
        qr_data = f"http://127.0.0.1:8000{qr_url}"
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save to BytesIO
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    # Save to vehicle
    from django.core.files import File
    vehicle.qr_code.save(f'qr_{vehicle.qr_unique_id}.png', File(buffer), save=True)


@login_required
def customize_qr(request, pk):
    """View for customizing QR code appearance"""
    vehicle = get_object_or_404(Vehicle, pk=pk, user=request.user)
    
    # Check if user has custom QR design feature
    user_plan = request.user.current_plan
    if not user_plan or not user_plan.custom_qr_design:
        messages.error(request, 'Custom QR design is not available in your current plan.')
        return redirect('vehicle_detail', pk=pk)
    
    if request.method == 'POST':
        form = QRCodeCustomizationForm(request.POST)
        if form.is_valid():
            # Apply customization and regenerate QR code
            # This would integrate with a QR code generation service
            messages.success(request, 'QR code customized successfully!')
            return redirect('vehicle_detail', pk=pk)
    else:
        form = QRCodeCustomizationForm()
    
    context = {
        'form': form,
        'vehicle': vehicle,
    }
    return render(request, 'parking/customize_qr.html', context)


@login_required
def subscription_plans(request):
    """View for subscription plans"""
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
    
    context = {
        'plans': plans,
        'current_plan': request.user.current_plan,
    }
    return render(request, 'parking/subscription_plans.html', context)


@login_required
def select_plan(request, plan_id):
    """View for selecting a subscription plan"""
    plan = get_object_or_404(SubscriptionPlan, pk=plan_id, is_active=True)
    
    if request.method == 'POST':
        form = SubscriptionPlanSelectionForm(request.POST)
        if form.is_valid():
            # Process subscription
            # In a real application, this would integrate with payment processing
            messages.success(request, f'Successfully subscribed to {plan.name}!')
            return redirect('parking:subscription_plans')
    else:
        form = SubscriptionPlanSelectionForm()
    
    context = {
        'form': form,
        'plan': plan,
    }
    return render(request, 'parking/select_plan.html', context)


@login_required
def parking_sessions(request):
    """View for parking sessions"""
    sessions = ParkingSession.objects.filter(vehicle__user=request.user).order_by('-start_time')
    
    context = {
        'sessions': sessions,
    }
    return render(request, 'parking/parking_sessions.html', context)


@login_required
def start_parking_session(request, vehicle_id):
    """View for starting a parking session"""
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id, user=request.user)
    
    if request.method == 'POST':
        form = ParkingSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.vehicle = vehicle
            session.status = 'active'
            session.save()
            
            messages.success(request, 'Parking session started!')
            return redirect('parking:parking_sessions')
    else:
        form = ParkingSessionForm()
    
    context = {
        'form': form,
        'vehicle': vehicle,
    }
    return render(request, 'parking/start_parking_session.html', context)


@login_required
@require_POST
def end_parking_session(request, session_id):
    """View for ending a parking session"""
    session = get_object_or_404(ParkingSession, pk=session_id, vehicle__user=request.user)
    
    if session.status == 'active':
        session.status = 'completed'
        session.end_time = timezone.now()
        session.save()
        messages.success(request, 'Parking session ended!')
    else:
        messages.error(request, 'This parking session is already completed.')
    
    return redirect('parking:parking_sessions')


def scan_qr_code(request, qr_id):
    """Public view for scanning QR codes"""
    try:
        vehicle = Vehicle.objects.get(qr_unique_id=qr_id, is_qr_active=True)
        
        # Record the scan
        QRCodeScan.objects.create(
            vehicle=vehicle,
            scanned_by_ip=request.META.get('REMOTE_ADDR'),
            scanned_by_user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
        
        # Get contact information based on visibility settings
        contact_info = vehicle.get_contact_info()
        
        context = {
            'vehicle': vehicle,
            'contact_info': contact_info,
        }
        return render(request, 'parking/scan_result.html', context)
        
    except Vehicle.DoesNotExist:
        messages.error(request, 'Invalid or inactive QR code.')
        return redirect('home')


@csrf_exempt
def contact_owner_api(request, qr_id):
    """API endpoint for contacting vehicle owner"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        vehicle = Vehicle.objects.get(qr_unique_id=qr_id, is_qr_active=True)
        data = json.loads(request.body)
        
        reason = data.get('reason')
        message = data.get('message', '')
        contact_method = data.get('contact_method', 'call')
        
        # In a real application, you would:
        # 1. Send notification to vehicle owner
        # 2. Log the contact request
        # 3. Handle SMS/call routing
        
        return JsonResponse({
            'message': 'Contact request sent successfully',
            'vehicle_id': str(vehicle.qr_unique_id),
            'contact_method': contact_method
        })
        
    except Vehicle.DoesNotExist:
        return JsonResponse({'error': 'Vehicle not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def search_vehicle(request):
    """Public view for searching vehicles"""
    if request.method == 'POST':
        form = VehicleSearchForm(request.POST)
        if form.is_valid():
            query = form.cleaned_data['search_query']
            
            # Search by license plate or QR code
            vehicles = Vehicle.objects.filter(
                Q(license_plate__icontains=query) | 
                Q(qr_unique_id__icontains=query),
                is_qr_active=True
            )
            
            context = {
                'form': form,
                'vehicles': vehicles,
                'query': query,
            }
            return render(request, 'parking/search_results.html', context)
    else:
        form = VehicleSearchForm()
    
    context = {
        'form': form,
    }
    return render(request, 'parking/search_vehicle.html', context)
