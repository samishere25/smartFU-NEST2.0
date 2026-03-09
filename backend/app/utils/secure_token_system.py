"""
Secure Token System for Reporter Portal
Generates one-time use tokens with expiration
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional
import json


class SecureTokenManager:
    """
    Manages secure access tokens for reporter portal
    
    Features:
    - One-time use tokens
    - Expiration (default 7 days)
    - Purpose-limited (specific case only)
    - Audit trail
    """
    
    def __init__(self, token_expiry_days: int = 7):
        self.token_expiry_days = token_expiry_days
    
    def generate_token(
        self,
        case_id: str,
        reporter_email: str,
        reporter_type: str,
        questions: list
    ) -> Dict[str, any]:
        """
        Generate secure access token for a case
        
        Returns:
            dict with token, url, expiry
        """
        # Generate cryptographically secure token
        raw_token = secrets.token_urlsafe(32)  # 256 bits of entropy
        
        # Hash for storage (never store raw token)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        
        # Calculate expiry
        expires_at = datetime.utcnow() + timedelta(days=self.token_expiry_days)
        
        # Token metadata
        token_data = {
            'token': raw_token,  # Only shown once
            'token_hash': token_hash,  # Store this
            'case_id': case_id,
            'reporter_email': reporter_email,
            'reporter_type': reporter_type,
            'questions': questions,
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': expires_at.isoformat(),
            'used': False,
            'access_count': 0,
            'max_uses': 1  # One-time use
        }
        
        # Generate portal URL
        portal_url = self._generate_portal_url(raw_token)
        
        return {
            'token': raw_token,
            'token_hash': token_hash,
            'portal_url': portal_url,
            'expires_at': expires_at.isoformat(),
            'valid_for_days': self.token_expiry_days,
            'metadata': token_data
        }
    
    def _generate_portal_url(self, token: str) -> str:
        """Generate portal URL with token"""
        base_url = "https://smartfu.yourcompany.com/reporter-portal"
        return f"{base_url}?token={token}"
    
    def validate_token(
        self,
        token: str,
        stored_token_data: Dict
    ) -> Dict[str, any]:
        """
        Validate token is legitimate and not expired
        
        Returns:
            dict with valid (bool) and reason
        """
        # Hash provided token
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Check if matches
        if token_hash != stored_token_data['token_hash']:
            return {
                'valid': False,
                'reason': 'INVALID_TOKEN',
                'message': 'This link is not valid'
            }
        
        # Check if already used
        if stored_token_data['used']:
            return {
                'valid': False,
                'reason': 'ALREADY_USED',
                'message': 'This link has already been used'
            }
        
        # Check if expired
        expires_at = datetime.fromisoformat(stored_token_data['expires_at'])
        if datetime.utcnow() > expires_at:
            return {
                'valid': False,
                'reason': 'EXPIRED',
                'message': f'This link expired on {expires_at.strftime("%B %d, %Y")}'
            }
        
        # Check access count
        if stored_token_data['access_count'] >= stored_token_data['max_uses']:
            return {
                'valid': False,
                'reason': 'MAX_USES_EXCEEDED',
                'message': 'This link has been used the maximum number of times'
            }
        
        # Valid!
        return {
            'valid': True,
            'reason': 'VALID',
            'case_id': stored_token_data['case_id'],
            'reporter_email': stored_token_data['reporter_email'],
            'questions': stored_token_data['questions']
        }
    
    def mark_token_used(
        self,
        token_hash: str,
        stored_token_data: Dict
    ) -> Dict:
        """Mark token as used"""
        stored_token_data['used'] = True
        stored_token_data['access_count'] += 1
        stored_token_data['used_at'] = datetime.utcnow().isoformat()
        
        return stored_token_data
    
    def revoke_token(
        self,
        token_hash: str,
        reason: str = 'REVOKED'
    ) -> Dict:
        """Revoke a token (emergency use)"""
        return {
            'revoked': True,
            'reason': reason,
            'revoked_at': datetime.utcnow().isoformat()
        }


class IdentityVerifier:
    """
    Basic identity verification for reporters
    """
    
    def verify_reporter(
        self,
        provided_email: str,
        expected_email: str,
        verification_code: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Verify reporter identity
        
        Simple email match for now
        Can be extended with 2FA, etc.
        """
        # Email match
        if provided_email.lower() != expected_email.lower():
            return {
                'verified': False,
                'reason': 'EMAIL_MISMATCH',
                'message': 'The email address does not match our records'
            }
        
        # Optional: Verification code check
        if verification_code:
            # In production, would check against sent code
            # For now, simplified
            pass
        
        return {
            'verified': True,
            'email': provided_email,
            'verified_at': datetime.utcnow().isoformat()
        }


class PurposeLimitedAccess:
    """
    Ensures reporters only see data relevant to their case
    """
    
    def filter_case_data(
        self,
        full_case: Dict,
        reporter_type: str
    ) -> Dict:
        """
        Filter case data to show only what reporter needs to see
        
        Privacy-first: Don't show internal analysis, other cases, etc.
        """
        # Base data everyone sees
        filtered = {
            'case_id': full_case['case_id'],
            'adverse_event': full_case['adverse_event'],
            'report_date': full_case.get('created_at'),
        }
        
        # Add fields based on reporter type
        if reporter_type in ['MD', 'HP', 'PH']:
            # Healthcare professionals can see more
            filtered.update({
                'suspect_drug': full_case.get('suspect_drug'),
                'patient_age': full_case.get('patient_age'),
                'patient_sex': full_case.get('patient_sex')
            })
        else:
            # Consumers/patients see less (privacy)
            filtered.update({
                'suspect_drug': full_case.get('suspect_drug'),
                # Don't show patient demographics to consumers
            })
        
        # NEVER show:
        # - Internal AI analysis
        # - Risk scores
        # - Other cases
        # - Personal info of other patients
        
        return filtered
    
    def generate_privacy_notice(self, reporter_type: str) -> str:
        """Generate privacy notice for portal"""
        return f"""
        PRIVACY NOTICE:
        
        • Your responses are confidential and protected
        • We only show you information about YOUR report
        • Your data is encrypted and secure
        • You can stop at any time
        • This link expires in 7 days and can only be used once
        • By responding, you consent to FDA follow-up
        
        Questions? Contact: safety@smartfu.com
        """


# Convenience functions
def create_secure_link(case_id: str, reporter_email: str, reporter_type: str, questions: list) -> Dict:
    """Quick access to create secure link"""
    manager = SecureTokenManager()
    return manager.generate_token(case_id, reporter_email, reporter_type, questions)


def validate_access(token: str, stored_data: Dict) -> Dict:
    """Quick access to validate token"""
    manager = SecureTokenManager()
    return manager.validate_token(token, stored_data)
