"""
Utility functions for parking app
"""
from django.contrib import messages
from django.shortcuts import redirect


def check_plan_limit(user, limit_type, current_count=None, redirect_url=None):
    """
    Check if user has reached their plan limit for a specific feature
    
    Args:
        user: User object
        limit_type: Type of limit to check ('vehicles', 'phone_numbers')
        current_count: Current count (optional, will be calculated if not provided)
        redirect_url: URL to redirect to if limit is reached
        
    Returns:
        tuple: (can_add: bool, message: str, current_count: int, max_allowed: int)
    """
    user_plan = user.current_plan
    
    if not user_plan:
        return False, "No active plan found. Please contact support.", 0, 0
    
    # Get the appropriate limit based on limit_type
    if limit_type == 'vehicles':
        max_allowed = user_plan.max_vehicles
        if current_count is None:
            from .models import Vehicle
            current_count = Vehicle.objects.filter(user=user).count()
    elif limit_type == 'phone_numbers':
        max_allowed = user_plan.max_phone_numbers
        if current_count is None:
            from accounts.models import UserPhoneNumber
            current_count = UserPhoneNumber.objects.filter(user=user).count()
    else:
        return False, f"Unknown limit type: {limit_type}", 0, 0
    
    can_add = current_count < max_allowed
    
    if not can_add:
        message = f'You have reached the maximum number of {limit_type.replace("_", " ")} ({max_allowed}) for your {user_plan.name} plan. Please upgrade to add more.'
    else:
        remaining = max_allowed - current_count
        message = f'You can add {remaining} more {limit_type.replace("_", " ")} on your {user_plan.name} plan.'
    
    return can_add, message, current_count, max_allowed


def check_plan_feature(user, feature_name):
    """
    Check if user's plan includes a specific feature
    
    Args:
        user: User object
        feature_name: Name of the feature to check
        
    Returns:
        bool: True if feature is available, False otherwise
    """
    user_plan = user.current_plan
    
    if not user_plan:
        return False
    
    # Map feature names to plan attributes
    feature_mapping = {
        'number_masking': 'number_masking',
        'custom_qr_design': 'custom_qr_design',
        'priority_support': 'priority_support',
        'analytics_dashboard': 'analytics_dashboard',
        'logo_placement': 'logo_placement',
        'custom_branding': 'custom_branding',
    }
    
    if feature_name not in feature_mapping:
        return False
    
    return getattr(user_plan, feature_mapping[feature_name], False)


def get_plan_upgrade_message(user, feature_or_limit):
    """
    Get a message encouraging user to upgrade for a specific feature or limit
    
    Args:
        user: User object
        feature_or_limit: Feature name or limit type
        
    Returns:
        str: Upgrade message
    """
    user_plan = user.current_plan
    plan_name = user_plan.name if user_plan else "current plan"
    
    if feature_or_limit in ['number_masking', 'custom_qr_design', 'priority_support', 'analytics_dashboard']:
        return f'This feature is not available on your {plan_name}. Upgrade to unlock {feature_or_limit.replace("_", " ").title()}!'
    elif feature_or_limit in ['vehicles', 'phone_numbers']:
        return f'You have reached your {plan_name} limit. Upgrade to add more {feature_or_limit.replace("_", " ")}!'
    else:
        return f'Upgrade your {plan_name} to unlock more features!'


def enforce_plan_limit(request, limit_type, redirect_url=None):
    """
    Decorator-like function to enforce plan limits in views
    
    Args:
        request: Django request object
        limit_type: Type of limit to check
        redirect_url: URL to redirect to if limit is reached
        
    Returns:
        HttpResponse or None: Redirect response if limit reached, None otherwise
    """
    can_add, message, current_count, max_allowed = check_plan_limit(
        request.user, limit_type
    )
    
    if not can_add:
        messages.error(request, message)
        if redirect_url:
            return redirect(redirect_url)
    
    return None
