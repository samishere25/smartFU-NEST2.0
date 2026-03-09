"""
Contact Resolver Service

Simulates sponsor CRM integration for demo purposes.
Maps FAERS primaryid to real contact information.
"""

import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class ContactResolver:
    """
    Resolves patient/reporter contact information for follow-up.
    
    In production, this would integrate with sponsor CRM systems.
    For demo purposes, uses hardcoded mapping of primaryids to real contacts.
    """
    
    # Hardcoded contact mapping for demo
    # Maps primaryid -> contact info
    CONTACT_MAP = {
        186031921: {
            "email": "swapnilchidrawar1012@gmail.com",
            "phone": "+919156763701",
            "language": "en"
        },
        185573372: {
            "email": "swapnilchidrawar1012@gmail.com",
            "phone": "+919156763701",
            "language": "en"
        },
        183671351: {
            "email": "swapnilchidrawar1012@gmail.com",
            "phone": "+919156763701",
            "language": "en"
        },
        183928001: {
            "email": "swapnilchidrawar1012@gmail.com",
            "phone": "+919156763701",
            "language": "en"
        },
        182647273: {
            "email": "swapnilchidrawar1012@gmail.com",
            "phone": "+919156763701",
            "language": "en"
        },
        186307922: {
            "email": "swapnilchidrawar1012@gmail.com",
            "phone": "+919156763701",
            "language": "en"
        },
        185302921: {
            "email": "swapnilchidrawar1012@gmail.com",
            "phone": "+919156763701",
            "language": "en"
        },
        184523001: {
            "email": "swapnilchidrawar1012@gmail.com",
            "phone": "+919156763701",
            "language": "en"
        },
        187234512: {
            "email": "swapnilchidrawar1012@gmail.com",
            "phone": "+919156763701",
            "language": "en"
        },
        188901234: {
            "email": "swapnilchidrawar1012@gmail.com",
            "phone": "+919156763701",
            "language": "en"
        },
        189123456: {
            "email": "swapnilchidrawar1012@gmail.com",
            "phone": "+919156763701",
            "language": "en"
        },
        190234567: {
            "email": "swapnilchidrawar1012@gmail.com",
            "phone": "+919156763701",
            "language": "en"
        }
    }
    
    # Fallback contact for demo/testing when primaryid not in map
    FALLBACK_CONTACT = {
        "email": "swapnilchidrawar1012@gmail.com",
        "phone": "+919156763701",
        "language": "en"
    }
    
    @staticmethod
    def resolve_contact(primaryid: int) -> Optional[Dict[str, str]]:
        """
        Resolve contact information for a given primaryid.
        
        Args:
            primaryid: FAERS case primaryid
            
        Returns:
            Dict with email, phone, language if found, else None
        """
        logger.info(f"🔍 ContactResolver: Looking up contact for primaryid={primaryid}")
        logger.info(f"🔍 ContactResolver: Available primaryids in map: {list(ContactResolver.CONTACT_MAP.keys())}")
        
        contact = ContactResolver.CONTACT_MAP.get(primaryid)
        
        if contact:
            logger.info(f"✅ ContactResolver: CONTACT FOUND for primaryid={primaryid}")
            logger.info(f"✅ ContactResolver: Email={contact.get('email')}, Phone={contact.get('phone')}")
        else:
            logger.warning(f"⚠️ ContactResolver: NO CONTACT IN MAP for primaryid={primaryid}")
            logger.info(f"ℹ️ ContactResolver: Using FALLBACK_CONTACT for demo purposes")
            contact = ContactResolver.FALLBACK_CONTACT.copy()
            logger.info(f"✅ ContactResolver: Fallback Email={contact.get('email')}, Phone={contact.get('phone')}")
        
        return contact

