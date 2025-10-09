"""
WhatsApp data extraction module

Handles extraction of messages and media from WhatsApp using 
Business API or Twilio WhatsApp API.
"""

from .whatsapp_extractor import WhatsAppExtractor

__all__ = ["WhatsAppExtractor"]