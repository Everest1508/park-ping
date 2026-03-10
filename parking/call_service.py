"""
Call Service for Connecting Users

This module handles connecting two phone numbers using the click-to-call API.
"""

import re
import requests
from typing import Optional, Dict, Any

class CallService:
    """
    Service to handle call connections between two phone numbers.
    """
    
    @classmethod
    def format_phone_number(cls, phone_number: str) -> str:
        """
        Format phone number.
        """
        digits = re.sub(r'\D', '', phone_number)
        
        if len(digits) >= 10:
            return digits[-10:]
        return digits
    
    @classmethod
    def connect_call(cls, owner_number: str, scanner_number: str, qr_id: str, base_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Connect two phone numbers using the provided API.
        """
        owner_formatted = cls.format_phone_number(owner_number)
        scanner_formatted = cls.format_phone_number(scanner_number)

        print(owner_formatted)
        print(scanner_formatted)
        
        url = "https://msg.msgclub.net/rest/services/clicktocall/sendclicktocall?AUTH_KEY=73efcfe5fedd98e5b108f456d2a8197"
        
        payload = {
            "routeId": "40",
            "senderId": "7317177510",
            "mobileNumbers": scanner_formatted,
            "agentNumbers": owner_formatted,
            "callInitiator": "client",
            "maxCallDuration": "2",
            "retryAttempt": "3",
            "retryDuration": "60"
        }
        
        try:
            response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            
            # The API returns a JSON response
            data = response.json() if response.content else {}
            
            return {
                'success': True,
                'call_sid': data.get('reqId', f'call_{qr_id[:8]}'), # Use reqId if available, else mockup
                'status': 'initiated',
                'owner_number': owner_formatted,
                'scanner_number': scanner_formatted,
                'message': 'Call initiated. You will be connected shortly.'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @classmethod
    def validate_phone_number(cls, phone_number: str) -> bool:
        """
        Validate phone number format.
        """
        digits = re.sub(r'\D', '', phone_number)
        return len(digits) >= 10 and len(digits) <= 15
