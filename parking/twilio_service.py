"""
Twilio Service for Call Connection

This module handles connecting two phone numbers using Twilio.
When a QR code is scanned with masking enabled, the scanner enters their number,
and Twilio connects both the owner's number and scanner's number.
"""

import re
from typing import Optional, Dict, Any
from django.conf import settings


class TwilioCallService:
    """
    Service to handle Twilio call connections between two phone numbers.
    """
    
    @classmethod
    def format_phone_number(cls, phone_number: str) -> str:
        """
        Format phone number to E.164 format for Twilio.
        
        Args:
            phone_number: Phone number in any format
            
        Returns:
            Phone number in E.164 format (e.g., +1234567890)
        """
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone_number)
        
        # If it doesn't start with +, add country code
        # For Indian numbers, add +91 if not present
        if not phone_number.startswith('+'):
            # Check if it's an Indian number (starts with 0 or doesn't have country code)
            if digits.startswith('0'):
                digits = digits[1:]  # Remove leading 0
            if len(digits) == 10:
                # Assume Indian number
                return f'+91{digits}'
            elif len(digits) == 11 and digits.startswith('91'):
                return f'+{digits}'
            elif len(digits) >= 10:
                # For other countries, try to detect
                # If 10 digits, assume US/Canada (+1)
                if len(digits) == 10:
                    return f'+1{digits}'
                # Otherwise, add + prefix
                return f'+{digits}'
        
        return phone_number if phone_number.startswith('+') else f'+{digits}'
    
    @classmethod
    def connect_call(cls, owner_number: str, scanner_number: str, qr_id: str, base_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Connect two phone numbers using Twilio.
        
        This creates a call that connects both parties:
        1. Twilio calls the owner's number
        2. When owner answers, Twilio calls the scanner's number
        3. Both parties are connected
        
        Args:
            owner_number: The vehicle owner's phone number
            scanner_number: The scanner's phone number (from QR scan)
            qr_id: The QR code unique ID for tracking
            
        Returns:
            Dictionary with call status and details
        """
        try:
            from twilio.rest import Client
            from twilio.twiml.voice_response import VoiceResponse
            
            # Get Twilio credentials from settings
            account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
            auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
            twilio_number = getattr(settings, 'TWILIO_PHONE_NUMBER', None)
            
            if not all([account_sid, auth_token, twilio_number]):
                return {
                    'success': False,
                    'error': 'Twilio credentials not configured'
                }
            
            # Initialize Twilio client
            client = Client(account_sid, auth_token)
            
            # Format phone numbers
            owner_formatted = cls.format_phone_number(owner_number)
            scanner_formatted = cls.format_phone_number(scanner_number)
            
            # Get the base URL for TwiML
            if not base_url:
                base_url = getattr(settings, 'BASE_URL', None)
            
            if not base_url:
                return {
                    'success': False,
                    'error': 'BASE_URL not configured. Please set BASE_URL in settings.py to a publicly accessible URL.'
                }
            
            # Validate that base_url is not localhost (Twilio requires public URL)
            if 'localhost' in base_url.lower() or '127.0.0.1' in base_url.lower():
                return {
                    'success': False,
                    'error': 'BASE_URL cannot be localhost. Twilio requires a publicly accessible URL. For local development, use ngrok or similar tool to expose your local server.'
                }
            
            connect_url = f"{base_url.rstrip('/')}/parking/qr/{qr_id}/twilio-connect/"
            
            # Create the call - Twilio will call the owner first
            # When owner answers, Twilio will execute the TwiML at connect_url
            # which will then call the scanner and connect them
            call = client.calls.create(
                to=owner_formatted,
                from_=twilio_number,
                url=connect_url,
                method='POST',
                status_callback=f"{base_url.rstrip('/')}/parking/qr/{qr_id}/twilio-status/",
                status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
                status_callback_method='POST',
            )
            
            return {
                'success': True,
                'call_sid': call.sid,
                'status': call.status,
                'owner_number': owner_formatted,
                'scanner_number': scanner_formatted,
                'message': 'Call initiated. You will be connected shortly.'
            }
            
        except ImportError:
            return {
                'success': False,
                'error': 'Twilio library not installed. Please install: pip install twilio'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @classmethod
    def generate_twiml_for_connection(cls, scanner_number: str) -> str:
        """
        Generate TwiML to connect the scanner's number after owner answers.
        
        Args:
            scanner_number: The scanner's phone number to connect
            
        Returns:
            TwiML XML string
        """
        from twilio.twiml.voice_response import VoiceResponse, Dial
        from django.conf import settings
        
        response = VoiceResponse()
        
        # Say a message to the owner
        response.say('Connecting you now. Please hold.', voice='alice', language='en-US')
        
        # Get Twilio number for caller ID
        twilio_number = getattr(settings, 'TWILIO_PHONE_NUMBER', None)
        
        # Format scanner number
        scanner_formatted = cls.format_phone_number(scanner_number)
        
        # Dial the scanner's number
        # Use Twilio number as caller_id (or omit it to use default)
        if twilio_number:
            dial = Dial(caller_id=twilio_number)
        else:
            dial = Dial()
        
        dial.number(scanner_formatted)
        response.append(dial)
        
        return str(response)
    
    @classmethod
    def validate_phone_number(cls, phone_number: str) -> bool:
        """
        Validate phone number format.
        
        Args:
            phone_number: Phone number to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone_number)
        
        # Check if it has at least 10 digits
        return len(digits) >= 10 and len(digits) <= 15
