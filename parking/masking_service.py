"""
Mock Phone Number Masking Service

This module provides mock functions for phone number masking functionality.
In production, these would be replaced with actual masking service API calls.
"""

import random
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from django.utils import timezone
from django.conf import settings


class MockMaskingService:
    """
    Mock implementation of a phone number masking service.
    
    In production, this would interface with services like:
    - Twilio Proxy
    - Vonage Number Masking
    - Custom masking solutions
    """
    
    # Mock configuration
    MASKING_DURATION_MINUTES = getattr(settings, 'MASKING_DURATION_MINUTES', 30)
    MASKING_PREFIX = getattr(settings, 'MASKING_PREFIX', '+1555')  # Mock prefix
    
    @classmethod
    def generate_masked_number(cls, original_number: str) -> str:
        """
        Generate a mock masked phone number.
        
        Args:
            original_number: The original phone number to mask
            
        Returns:
            A mock masked phone number
        """
        # Remove any non-digit characters from original number
        clean_number = ''.join(filter(str.isdigit, original_number))
        
        # Generate a mock masked number using the prefix + random digits
        # In production, this would be handled by the masking service
        random_suffix = ''.join(random.choices(string.digits, k=7))
        masked_number = f"{cls.MASKING_PREFIX}{random_suffix}"
        
        return masked_number
    
    @classmethod
    def create_masking_session(cls, original_number: str, duration_minutes: Optional[int] = None) -> Dict[str, Any]:
        """
        Create a new masking session.
        
        Args:
            original_number: The original phone number to mask
            duration_minutes: Duration in minutes (defaults to MASKING_DURATION_MINUTES)
            
        Returns:
            Dictionary containing session details
        """
        if duration_minutes is None:
            duration_minutes = cls.MASKING_DURATION_MINUTES
            
        masked_number = cls.generate_masked_number(original_number)
        expires_at = timezone.now() + timedelta(minutes=duration_minutes)
        
        return {
            'masked_number': masked_number,
            'original_number': original_number,
            'expires_at': expires_at,
            'session_id': cls._generate_session_id(),
            'status': 'active'
        }
    
    @classmethod
    def get_active_session(cls, vehicle_id: str, original_number: str) -> Optional[Dict[str, Any]]:
        """
        Get an active masking session for a vehicle and phone number.
        
        Args:
            vehicle_id: The vehicle ID
            original_number: The original phone number
            
        Returns:
            Active session details or None if no active session
        """
        # In production, this would query the masking service API
        # For now, we'll return None to always create new sessions
        return None
    
    @classmethod
    def extend_session(cls, session_id: str, additional_minutes: int) -> Dict[str, Any]:
        """
        Extend an existing masking session.
        
        Args:
            session_id: The session ID to extend
            additional_minutes: Minutes to add to the session
            
        Returns:
            Updated session details
        """
        # Mock implementation - in production this would call the masking service
        return {
            'session_id': session_id,
            'extended_by_minutes': additional_minutes,
            'new_expires_at': timezone.now() + timedelta(minutes=additional_minutes),
            'status': 'extended'
        }
    
    @classmethod
    def terminate_session(cls, session_id: str) -> Dict[str, Any]:
        """
        Terminate a masking session.
        
        Args:
            session_id: The session ID to terminate
            
        Returns:
            Termination confirmation
        """
        # Mock implementation
        return {
            'session_id': session_id,
            'status': 'terminated',
            'terminated_at': timezone.now()
        }
    
    @classmethod
    def get_session_status(cls, session_id: str) -> Dict[str, Any]:
        """
        Get the status of a masking session.
        
        Args:
            session_id: The session ID to check
            
        Returns:
            Session status information
        """
        # Mock implementation
        return {
            'session_id': session_id,
            'status': 'active',
            'expires_at': timezone.now() + timedelta(minutes=30),
            'calls_made': 0
        }
    
    @classmethod
    def _generate_session_id(cls) -> str:
        """Generate a unique session ID."""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    
    @classmethod
    def validate_phone_number(cls, phone_number: str) -> bool:
        """
        Validate if a phone number is in correct format.
        
        Args:
            phone_number: Phone number to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Basic validation - remove non-digits and check length
        clean_number = ''.join(filter(str.isdigit, phone_number))
        return len(clean_number) >= 10 and len(clean_number) <= 15


# Convenience functions for easy import
def create_masking_session(original_number: str, duration_minutes: Optional[int] = None) -> Dict[str, Any]:
    """Create a new masking session."""
    return MockMaskingService.create_masking_session(original_number, duration_minutes)


def get_active_session(vehicle_id: str, original_number: str) -> Optional[Dict[str, Any]]:
    """Get an active masking session."""
    return MockMaskingService.get_active_session(vehicle_id, original_number)


def generate_masked_number(original_number: str) -> str:
    """Generate a masked phone number."""
    return MockMaskingService.generate_masked_number(original_number)


def validate_phone_number(phone_number: str) -> bool:
    """Validate a phone number format."""
    return MockMaskingService.validate_phone_number(phone_number)

