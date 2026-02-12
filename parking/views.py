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
    QRCodeScan, UserSubscription, VehicleContact
)
from .forms import (
    VehicleForm, ParkingSessionForm, QRCodeCustomizationForm,
    SubscriptionPlanSelectionForm, VehicleSearchForm, ContactOwnerForm
)
from accounts.models import CustomUser, UserPhoneNumber
from django.conf import settings


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
    
    # Get user's phone numbers for primary contact dropdown
    user_phone_numbers = UserPhoneNumber.objects.filter(user=request.user).order_by('-is_primary', 'created_at')
    
    if request.method == 'POST':
        form = VehicleForm(request.POST, user=request.user)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.user = request.user
            
            # Get primary contact from dropdown (required)
            primary_phone_key = 'primary_contact_phone'
            
            if primary_phone_key not in request.POST or not request.POST.get(primary_phone_key, '').strip():
                messages.error(request, 'Primary contact number is required.')
                context = {
                    'form': form,
                    'user_plan': user_plan,
                    'max_vehicles': max_vehicles,
                    'can_add_vehicle': current_count < max_vehicles,
                    'user_phone_numbers': user_phone_numbers,
                    'phone_numbers': user_phone_numbers,
                    'vehicles': Vehicle.objects.filter(user=request.user),
                    'active_qr_count': Vehicle.objects.filter(user=request.user, is_qr_active=True).count(),
                }
                return render(request, 'parking/add_vehicle.html', context)
            
            vehicle.save()
            
            # Save primary contact (required) - no relation needed, it's the owner's number
            primary_phone = request.POST.get(primary_phone_key, '').strip()
            
            VehicleContact.objects.create(
                vehicle=vehicle,
                phone_number=primary_phone,
                relation='family',  # Default relation for owner's number
                is_primary=True,
                show_in_qr=True
            )
            
            # Get or create UserPhoneNumber for primary contact
            user_phone = UserPhoneNumber.objects.filter(
                user=request.user,
                phone_number=primary_phone
            ).first()
            
            if not user_phone:
                user_phone = UserPhoneNumber.objects.create(
                    user=request.user,
                    phone_number=primary_phone,
                    is_primary=False,  # Don't override existing primary
                    label="Vehicle Owner Contact"
                )
            
            # Set as contact_phone for the vehicle (required for masking)
            vehicle.contact_phone = user_phone
            vehicle.save()
            
            # Save additional contacts (optional)
            contact_count = 1  # Start from 1, since 0 is primary
            while True:
                phone_key = f'contact_phone_{contact_count}'
                relation_key = f'contact_relation_{contact_count}'
                
                if phone_key in request.POST and relation_key in request.POST:
                    phone_number = request.POST.get(phone_key, '').strip()
                    relation = request.POST.get(relation_key, 'family').strip()
                    
                    if phone_number:  # Only save if phone number is provided
                        # Default to 'family' if relation is 'owner'
                        if relation == 'owner':
                            relation = 'family'
                        
                        VehicleContact.objects.create(
                            vehicle=vehicle,
                            phone_number=phone_number,
                            relation=relation,
                            is_primary=False,
                            show_in_qr=True
                        )
                    contact_count += 1
                else:
                    break
            
            # Generate QR code
            generate_qr_code(vehicle, request)
            
            messages.success(request, 'Vehicle added successfully!')
            return redirect('parking:vehicle_list')
        else:
            # Form is not valid, show errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
            messages.error(request, 'Please correct the errors below and try again.')
    else:
        form = VehicleForm(user=request.user)
    
    # Calculate stats
    vehicles = Vehicle.objects.filter(user=request.user)
    active_qr_count = vehicles.filter(is_qr_active=True).count()
    phone_numbers = UserPhoneNumber.objects.filter(user=request.user)
    
    context = {
        'form': form,
        'max_vehicles': max_vehicles,
        'current_count': current_count,
        'user_phone_numbers': user_phone_numbers,
        'phone_numbers': phone_numbers,
        'vehicles': vehicles,
        'active_qr_count': active_qr_count,
    }
    return render(request, 'parking/add_vehicle.html', context)


@login_required
def edit_vehicle(request, pk):
    """View for editing vehicles"""
    vehicle = get_object_or_404(Vehicle, pk=pk, user=request.user)
    
    # Get user's phone numbers for primary contact dropdown
    user_phone_numbers = UserPhoneNumber.objects.filter(user=request.user).order_by('-is_primary', 'created_at')
    
    if request.method == 'POST':
        form = VehicleForm(request.POST, instance=vehicle, user=request.user)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.user = request.user
            vehicle.save()
            
            # Get primary contact from dropdown (required)
            primary_phone_key = 'primary_contact_phone'
            primary_relation_key = 'primary_contact_relation'
            
            if primary_phone_key not in request.POST or not request.POST.get(primary_phone_key, '').strip():
                messages.error(request, 'Primary contact number is required.')
                context = {
                    'form': form,
                    'vehicle': vehicle,
                    'user_plan': request.user.current_plan,
                    'user_phone_numbers': user_phone_numbers,
                    'existing_contacts': vehicle.contacts.all(),
                }
                return render(request, 'parking/edit_vehicle.html', context)
            
            # Delete existing contacts and save new ones
            VehicleContact.objects.filter(vehicle=vehicle).delete()
            
            # Save primary contact (required) - no relation needed, it's the owner's number
            primary_phone = request.POST.get(primary_phone_key, '').strip()
            
            VehicleContact.objects.create(
                vehicle=vehicle,
                phone_number=primary_phone,
                relation='family',  # Default relation for owner's number
                is_primary=True,
                show_in_qr=True
            )
            
            # Get or create UserPhoneNumber for primary contact
            user_phone = UserPhoneNumber.objects.filter(
                user=request.user,
                phone_number=primary_phone
            ).first()
            
            if not user_phone:
                user_phone = UserPhoneNumber.objects.create(
                    user=request.user,
                    phone_number=primary_phone,
                    is_primary=False,  # Don't override existing primary
                    label="Vehicle Owner Contact"
                )
            
            # Set as contact_phone for the vehicle (required for masking)
            vehicle.contact_phone = user_phone
            vehicle.save()
            
            # Save additional contacts (optional)
            contact_count = 1  # Start from 1, since 0 is primary
            while True:
                phone_key = f'contact_phone_{contact_count}'
                relation_key = f'contact_relation_{contact_count}'
                
                if phone_key in request.POST and relation_key in request.POST:
                    phone_number = request.POST.get(phone_key, '').strip()
                    relation = request.POST.get(relation_key, 'family').strip()
                    
                    if phone_number:  # Only save if phone number is provided
                        # Default to 'family' if relation is 'owner'
                        if relation == 'owner':
                            relation = 'family'
                        
                        VehicleContact.objects.create(
                            vehicle=vehicle,
                            phone_number=phone_number,
                            relation=relation,
                            is_primary=False,
                            show_in_qr=True
                        )
                    contact_count += 1
                else:
                    break
            
            messages.success(request, 'Vehicle updated successfully!')
            return redirect('parking:vehicle_list')
        else:
            # Form is not valid, show errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
            messages.error(request, 'Please correct the errors below and try again.')
    else:
        form = VehicleForm(instance=vehicle, user=request.user)
    
    # Get existing contacts for the vehicle
    existing_contacts = VehicleContact.objects.filter(vehicle=vehicle).order_by('-is_primary', 'created_at')
    
    context = {
        'form': form,
        'vehicle': vehicle,
        'user_plan': request.user.current_plan,
        'user_phone_numbers': user_phone_numbers,
        'existing_contacts': existing_contacts,
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


def generate_qr_code(vehicle, request=None, custom_settings=None):
    """Generate QR code for a vehicle with optional customization"""
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
    
    # Get customization settings from vehicle or custom_settings parameter
    if custom_settings:
        primary_color = custom_settings.get('primary_color', vehicle.qr_primary_color)
        secondary_color = custom_settings.get('secondary_color', vehicle.qr_secondary_color)
        include_logo = custom_settings.get('include_logo', vehicle.qr_include_logo)
        logo_size = custom_settings.get('logo_size', vehicle.qr_logo_size)
        qr_size = custom_settings.get('qr_size', vehicle.qr_size)
    else:
        primary_color = vehicle.qr_primary_color
        secondary_color = vehicle.qr_secondary_color
        include_logo = vehicle.qr_include_logo
        logo_size = vehicle.qr_logo_size
        qr_size = vehicle.qr_size
    
    # Convert hex colors to RGB tuples for PIL compatibility
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    primary_rgb = hex_to_rgb(primary_color)
    secondary_rgb = hex_to_rgb(secondary_color)
    
    # Set QR code size based on settings
    size_mapping = {
        'small': {'box_size': 8, 'border': 4, 'target_size': 200},
        'medium': {'box_size': 12, 'border': 6, 'target_size': 300},
        'large': {'box_size': 16, 'border': 8, 'target_size': 400}
    }
    
    qr_config = size_mapping.get(qr_size, size_mapping['medium'])
    
    # Generate QR code with custom styling
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,  # Better error correction
        box_size=qr_config['box_size'],
        border=qr_config['border'],
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    try:
        from qrcode.image.styledpil import StyledPilImage
        from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
        from qrcode.image.styles.colormasks import SolidFillColorMask
        
        # Create styled QR code with rounded corners
        img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=RoundedModuleDrawer(),
            color_mask=SolidFillColorMask(
                back_color=secondary_rgb,
                front_color=primary_rgb
            )
        )
    except (ImportError, Exception):
        # Fallback to basic styled QR code if advanced styling isn't available
        img = qr.make_image(
            fill_color=primary_rgb,
            back_color=secondary_rgb
        )
    
    # Add PARKPING branding in the center of QR code (if enabled)
    if include_logo:
        try:
            from PIL import Image, ImageDraw, ImageFont
            import os
            
            # Convert to PIL Image for editing
            img = img.convert('RGBA')
            width, height = img.size
            
            # Create center branding area
            center_x, center_y = width // 2, height // 2
            
            # Set logo size based on settings
            logo_size_mapping = {
                'small': min(width, height) // 8,
                'medium': min(width, height) // 6,
                'large': min(width, height) // 4
            }
            logo_size = logo_size_mapping.get(logo_size, logo_size_mapping['medium'])
            
            # Create overlay for the center logo
            overlay = Image.new('RGBA', (width, height), (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)
            
            # Try to load a font for the text
            try:
                # Try to use a system font - make it bigger
                font_size = logo_size // 2  # Increased from logo_size // 3
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            except:
                try:
                    # Fallback font
                    font = ImageFont.load_default()
                except:
                    font = None
            
            # Draw PARKPING text with background
            text = "PARKPING"
            if font:
                # Get text dimensions
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                # Position text in center
                text_x = center_x - text_width // 2
                text_y = center_y - text_height // 2
                
                # Draw background rectangle for text - adjust for better centering
                padding = 6  # Increased padding for bigger text
                vertical_padding = 3  # Extra vertical padding to center text better
                draw.rectangle([
                    text_x - padding, text_y - vertical_padding,
                    text_x + text_width + padding, text_y + text_height + padding + 14
                ], fill=secondary_rgb + (255,))  # Use secondary color as background
                
                # Draw text
                draw.text((text_x, text_y), text, fill=primary_rgb, font=font)
            else:
                # Fallback: draw simple text without font with background
                text_x = center_x - 40  # Adjusted for bigger text area
                text_y = center_y - 6   # Adjusted for better vertical centering
                
                # Draw background rectangle - bigger for larger text with better centering
                draw.rectangle([
                    text_x - 6, text_y - 8,  # Extra top padding
                    text_x + 80, text_y + 18  # Balanced bottom padding
                ], fill=secondary_rgb + (255,))  # Use secondary color as background
                
                # Draw text
                draw.text((text_x, text_y), "PARKPING", fill=primary_rgb)
            
            # Composite the overlay onto the QR code
            img = Image.alpha_composite(img, overlay)
            img = img.convert('RGB')  # Convert back to RGB for saving
            
        except (ImportError, Exception) as e:
            # If PIL operations fail, continue with the original QR code
            pass
    
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
        return redirect('parking:vehicle_detail', pk=pk)
    
    if request.method == 'POST':
        form = QRCodeCustomizationForm(request.POST)
        if form.is_valid():
            # Save customization settings to vehicle
            vehicle.qr_primary_color = form.cleaned_data['primary_color']
            vehicle.qr_secondary_color = form.cleaned_data['secondary_color']
            vehicle.qr_include_logo = form.cleaned_data['include_logo']
            vehicle.qr_logo_size = form.cleaned_data['logo_size']
            vehicle.qr_size = form.cleaned_data['qr_size']
            vehicle.save()
            
            # Regenerate QR code with new settings
            try:
                generate_qr_code(vehicle, request)
                messages.success(request, 'QR code customized successfully!')
            except Exception as e:
                messages.error(request, f'Error customizing QR code: {str(e)}')
            
            return redirect('parking:vehicle_detail', pk=pk)
    else:
        # Initialize form with current vehicle settings
        form = QRCodeCustomizationForm(initial={
            'primary_color': vehicle.qr_primary_color,
            'secondary_color': vehicle.qr_secondary_color,
            'include_logo': vehicle.qr_include_logo,
            'logo_size': vehicle.qr_logo_size,
            'qr_size': vehicle.qr_size,
        })
    
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
            # Assign the plan to the user
            from django.utils import timezone
            from datetime import timedelta
            
            # Get billing cycle from form
            billing_cycle = form.cleaned_data.get('billing_cycle', 'monthly')
            
            # Update user's subscription
            request.user.current_plan = plan
            request.user.subscription_start_date = timezone.now()
            request.user.is_subscription_active = True
            
            if plan.price > 0:
                # Set end date based on billing cycle
                if billing_cycle == 'yearly':
                    # For yearly subscription
                    request.user.subscription_end_date = timezone.now() + timedelta(days=365)
                    success_message = f'Successfully subscribed to {plan.name} (Yearly)! You saved 20% on your subscription.'
                else:
                    # For monthly subscription
                    request.user.subscription_end_date = timezone.now() + timedelta(days=30)
                    success_message = f'Successfully subscribed to {plan.name} (Monthly)! Your plan is now active.'
            else:
                # Free plan has no end date
                request.user.subscription_end_date = None
                success_message = f'Successfully activated {plan.name}! Your plan is now active.'
                
            request.user.save()
            
            messages.success(request, success_message)
            return redirect('parking:subscription_plans')
        else:
            # Form is not valid, show errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
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
        
        # Get emergency numbers from settings
        from django.conf import settings
        emergency_numbers = getattr(settings, 'EMERGENCY_NUMBERS', {
            'police': '100',
            'ambulance': '102',
            'fire': '101',
            'women_helpline': '1091',
            'child_helpline': '1098',
            'roadside_assistance': '1033',
        })
        
        context = {
            'vehicle': vehicle,
            'contact_info': contact_info,
            'emergency_numbers': emergency_numbers,
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


@csrf_exempt
def get_masked_number_api(request, qr_id):
    """API endpoint to get masked phone number for calling"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        from .masking_service import MockMaskingService
        from .models import PhoneNumberMasking
        from django.utils import timezone
        from datetime import timedelta
        
        # Get the vehicle
        vehicle = Vehicle.objects.get(qr_unique_id=qr_id, is_qr_active=True)
        
        # Check if masking is enabled for this specific vehicle
        if not vehicle.masking_enabled:
            return JsonResponse({
                'error': 'Number masking is not enabled for this vehicle',
                'vehicle_masking_disabled': True
            }, status=403)
        
        # Masking is available for all plans
        # Check plan limits for concurrent masking sessions (if plan exists)
        user_plan = vehicle.user.current_plan
        max_sessions = 999  # Default unlimited for all plans
        
        if user_plan and user_plan.max_masking_sessions > 0:
            max_sessions = user_plan.max_masking_sessions
        
        active_sessions_count = PhoneNumberMasking.objects.filter(
            vehicle__user=vehicle.user,
            status='active',
            expires_at__gt=timezone.now()
        ).count()
        
        # Check if user has reached their session limit (only if limit is set)
        if max_sessions < 999 and active_sessions_count >= max_sessions:
            return JsonResponse({
                'error': f'You have reached the maximum number of concurrent masking sessions ({max_sessions}). Please wait for existing sessions to expire.',
                'limit_reached': True,
                'current_sessions': active_sessions_count,
                'max_sessions': max_sessions,
                'plan_name': user_plan.name if user_plan else 'Your Plan'
            }, status=403)
        
        # Get the original phone number
        if not vehicle.contact_phone:
            return JsonResponse({'error': 'No contact phone number available'}, status=404)
        
        original_phone = vehicle.contact_phone.phone_number
        
        # Check for existing active masking session
        active_session = PhoneNumberMasking.objects.filter(
            vehicle=vehicle,
            original_phone=original_phone,
            status='active',
            expires_at__gt=timezone.now()
        ).first()
        
        if active_session:
            # Return existing masked number
            active_session.increment_call_count()
            return JsonResponse({
                'success': True,
                'masked_number': active_session.masked_phone,
                'original_number': original_phone,
                'session_id': str(active_session.session_id),
                'expires_at': active_session.expires_at.isoformat(),
                'is_existing': True,
                'call_count': active_session.call_count
            })
        
        # Create new masking session
        masking_data = MockMaskingService.create_masking_session(original_phone)
        
        # Save to database
        masking_session = PhoneNumberMasking.objects.create(
            vehicle=vehicle,
            original_phone=original_phone,
            masked_phone=masking_data['masked_number'],
            expires_at=masking_data['expires_at'],
            call_count=1
        )
        
        return JsonResponse({
            'success': True,
            'masked_number': masking_data['masked_number'],
            'original_number': original_phone,
            'session_id': str(masking_session.session_id),
            'expires_at': masking_data['expires_at'].isoformat(),
            'is_existing': False,
            'call_count': 1
        })
        
    except Vehicle.DoesNotExist:
        return JsonResponse({'error': 'Vehicle not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def terminate_masking_session_api(request, qr_id):
    """API endpoint to terminate a masking session"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        from .models import PhoneNumberMasking
        from django.utils import timezone
        
        # Get the vehicle
        vehicle = Vehicle.objects.get(qr_unique_id=qr_id, is_qr_active=True)
        
        # Get session ID from request
        data = json.loads(request.body)
        session_id = data.get('session_id')
        
        if not session_id:
            return JsonResponse({'error': 'Session ID required'}, status=400)
        
        # Find and terminate the session
        masking_session = PhoneNumberMasking.objects.get(
            vehicle=vehicle,
            session_id=session_id,
            status='active'
        )
        
        masking_session.status = 'cancelled'
        masking_session.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Masking session terminated successfully',
            'session_id': str(session_id)
        })
        
    except Vehicle.DoesNotExist:
        return JsonResponse({'error': 'Vehicle not found'}, status=404)
    except PhoneNumberMasking.DoesNotExist:
        return JsonResponse({'error': 'Masking session not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def chatbot_api(request):
    """API endpoint for chatbot using Groq"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        from groq import Groq
        
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        # Initialize Groq client
        groq_api_key = getattr(settings, 'GROQ_API_KEY', None)
        if not groq_api_key:
            return JsonResponse({'error': 'Groq API key not configured'}, status=500)
        
        client = Groq(api_key=groq_api_key)
        
        # Platform context for the chatbot
        platform_context = """
You are a helpful assistant for ParkPing, a vehicle contact management platform. Here's what you need to know:

PARKPING PLATFORM CONTEXT:
- ParkPing helps vehicle owners create QR codes for their vehicles
- Users can add multiple vehicles and generate QR codes for each
- When someone scans the QR code, they can see contact information and emergency numbers
- Users can add multiple contact numbers with relations (Family Member, Friend, Colleague, Emergency Contact, Other)
- The platform supports number masking for privacy
- Users can customize QR code appearance (colors, size, logo)
- Emergency numbers available: Police (100), Ambulance (102), Fire (101), Women Helpline (1091), Child Helpline (1098), Traffic/Roadside (1033)
- ParkPing helpline: +1-800-727-5746
- Users can track parking sessions and QR code scans
- Subscription plans available: Free, Basic, Professional, Enterprise

FEATURES:
1. Vehicle Management: Add, edit, delete vehicles with details (make, model, year, color, license plate)
2. QR Code Generation: Automatic QR code generation for each vehicle
3. Contact Management: Multiple contacts per vehicle with relations
4. Privacy Settings: Control what information shows in QR codes
5. Number Masking: Premium feature to mask phone numbers
6. Parking Sessions: Track where and when you park
7. Emergency Services: Quick access to emergency numbers in QR scans

HELPFUL INFORMATION:
- To add a vehicle: Go to "My Vehicles" and click "Add Vehicle"
- To customize QR code: Go to vehicle details and click "Customize QR"
- To add contacts: When adding/editing a vehicle, use the "Add Contact" button
- Emergency numbers are automatically shown in scanned QR codes
- Users can enable/disable showing phone, name, email, and vehicle details

Be friendly, helpful, and provide accurate information about ParkPing features. If asked about something not in this context, politely say you're focused on helping with ParkPing.
"""
        
        # Create chat completion
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": platform_context
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=1024,
        )
        
        bot_response = chat_completion.choices[0].message.content
        
        return JsonResponse({
            'success': True,
            'response': bot_response
        })
        
    except ImportError:
        return JsonResponse({'error': 'Groq library not installed. Please install: pip install groq'}, status=500)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def initiate_twilio_call(request, qr_id):
    """
    API endpoint to initiate a Twilio call connection.
    Scanner enters their phone number, and Twilio connects both parties.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        from .twilio_service import TwilioCallService
        from .models import PhoneNumberMasking
        from django.utils import timezone
        from datetime import timedelta
        
        data = json.loads(request.body)
        scanner_number = data.get('phone_number', '').strip()
        owner_phone = data.get('owner_phone', '').strip()  # Get selected owner phone
        
        if not scanner_number:
            return JsonResponse({'error': 'Phone number is required'}, status=400)
        
        # Validate phone number
        if not TwilioCallService.validate_phone_number(scanner_number):
            return JsonResponse({'error': 'Invalid phone number format'}, status=400)
        
        # Get the vehicle
        vehicle = Vehicle.objects.get(qr_unique_id=qr_id, is_qr_active=True)
        
        # Note: Calls are always allowed via Twilio, regardless of masking_enabled setting
        # Masking is available for all plans
        # Check plan limits for concurrent masking sessions (if plan exists)
        user_plan = vehicle.user.current_plan
        max_sessions = 999  # Default unlimited for all plans
        
        if user_plan and user_plan.max_masking_sessions > 0:
            max_sessions = user_plan.max_masking_sessions
        
        active_sessions_count = PhoneNumberMasking.objects.filter(
            vehicle__user=vehicle.user,
            status='active',
            expires_at__gt=timezone.now()
        ).count()
        
        # Check if user has reached their session limit (only if limit is set)
        if max_sessions < 999 and active_sessions_count >= max_sessions:
            return JsonResponse({
                'error': f'You have reached the maximum number of concurrent masking sessions ({max_sessions}). Please wait for existing sessions to expire.',
                'limit_reached': True,
                'current_sessions': active_sessions_count,
                'max_sessions': max_sessions,
                'plan_name': user_plan.name if user_plan else 'Your Plan'
            }, status=403)
        
        # Get the owner phone number - use selected one or fallback to contact_phone
        if owner_phone:
            # Validate that the selected phone belongs to this vehicle's contacts
            contact = VehicleContact.objects.filter(
                vehicle=vehicle,
                phone_number=owner_phone,
                show_in_qr=True
            ).first()
            if contact:
                owner_number = owner_phone
            else:
                return JsonResponse({'error': 'Invalid contact selected'}, status=400)
        elif vehicle.contact_phone:
            owner_number = vehicle.contact_phone.phone_number
        else:
            # Try to get from contacts
            first_contact = vehicle.contacts.filter(show_in_qr=True).first()
            if first_contact:
                owner_number = first_contact.phone_number
            else:
                return JsonResponse({'error': 'No contact phone number available'}, status=404)
        
        # Get the base URL from request or settings
        # For Twilio, we need a publicly accessible URL
        base_url = getattr(settings, 'BASE_URL', None)
        if not base_url:
            # Try to get from request
            base_url = request.build_absolute_uri('/').rstrip('/')
            # If it's localhost, we need a public URL (use ngrok or similar)
            if 'localhost' in base_url or '127.0.0.1' in base_url:
                return JsonResponse({
                    'error': 'Twilio requires a publicly accessible URL. Please set BASE_URL in settings.py to your public URL (e.g., from ngrok for local development).',
                    'details': 'For local development, use ngrok: https://ngrok.com/'
                }, status=500)
        
        # Create or update masking session FIRST (before initiating call)
        # This ensures the session exists when Twilio calls back
        masking_session, created = PhoneNumberMasking.objects.get_or_create(
            vehicle=vehicle,
            original_phone=owner_number,
            defaults={
                'masked_phone': scanner_number,  # Store scanner number for reference
                'scanner_phone': scanner_number,
                'expires_at': timezone.now() + timedelta(minutes=30),
                'call_count': 0,
                'status': 'active',
            }
        )
        
        if not created:
            # Update existing session
            masking_session.scanner_phone = scanner_number
            masking_session.status = 'active'
            masking_session.expires_at = timezone.now() + timedelta(minutes=30)
            masking_session.save()
        
        # Now initiate Twilio call connection
        call_result = TwilioCallService.connect_call(
            owner_number=owner_number,
            scanner_number=scanner_number,
            qr_id=str(qr_id),
            base_url=base_url
        )
        
        if not call_result.get('success'):
            return JsonResponse({
                'error': call_result.get('error', 'Failed to initiate call'),
                'details': call_result
            }, status=500)
        
        # Update session with call SID
        masking_session.twilio_call_sid = call_result.get('call_sid')
        masking_session.increment_call_count()
        masking_session.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Call initiated. You will be connected shortly.',
            'call_sid': call_result.get('call_sid'),
            'status': call_result.get('status'),
            'session_id': str(masking_session.session_id)
        })
        
    except Vehicle.DoesNotExist:
        return JsonResponse({'error': 'Vehicle not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def twilio_connect_twiml(request, qr_id):
    """
    Twilio TwiML endpoint that connects the scanner's number when owner answers.
    This is called by Twilio when the owner picks up the phone.
    """
    try:
        from .twilio_service import TwilioCallService
        from .models import PhoneNumberMasking
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Get the masking session to find scanner's number
        # We'll get it from the most recent active session for this QR
        vehicle = Vehicle.objects.get(qr_unique_id=qr_id, is_qr_active=True)
        
        # Get the most recent active session
        session = PhoneNumberMasking.objects.filter(
            vehicle=vehicle,
            status='active',
            expires_at__gt=timezone.now()
        ).order_by('-created_at').first()
        
        if not session or not session.scanner_phone:
            # Log for debugging
            logger.error(f"No active session or scanner phone found for QR {qr_id}")
            from twilio.twiml.voice_response import VoiceResponse
            response = VoiceResponse()
            response.say('Sorry, we could not find the number to connect. Please try again.', voice='alice')
            return HttpResponse(str(response), content_type='text/xml')
        
        # Log for debugging
        logger.info(f"Connecting scanner {session.scanner_phone} for QR {qr_id}")
        
        # Generate TwiML to connect scanner's number
        twiml = TwilioCallService.generate_twiml_for_connection(session.scanner_phone)
        
        # Log the TwiML for debugging
        logger.info(f"Generated TwiML: {twiml}")
        
        return HttpResponse(twiml, content_type='text/xml')
        
    except Vehicle.DoesNotExist:
        from twilio.twiml.voice_response import VoiceResponse
        response = VoiceResponse()
        response.say('Vehicle not found.', voice='alice')
        return HttpResponse(str(response), content_type='text/xml')
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in twilio_connect_twiml: {str(e)}", exc_info=True)
        from twilio.twiml.voice_response import VoiceResponse
        response = VoiceResponse()
        response.say('An error occurred. Please try again.', voice='alice')
        return HttpResponse(str(response), content_type='text/xml')


@csrf_exempt
def twilio_status_callback(request, qr_id):
    """
    Twilio status callback endpoint for tracking call status.
    Optional - can be used for analytics and logging.
    """
    try:
        from .models import PhoneNumberMasking
        
        call_sid = request.POST.get('CallSid')
        call_status = request.POST.get('CallStatus')
        
        if call_sid:
            # Update masking session with call status
            session = PhoneNumberMasking.objects.filter(
                twilio_call_sid=call_sid
            ).first()
            
            if session:
                # You can store call status in the model if needed
                # For now, we'll just log it
                pass
        
        return HttpResponse(status=200)
        
    except Exception as e:
        return HttpResponse(status=200)  # Always return 200 to Twilio
