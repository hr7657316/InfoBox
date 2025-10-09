"""
Email data extraction module

Handles extraction of emails and attachments from IMAP-compatible 
mail servers with OAuth2 and app password authentication.
"""

from .email_extractor import EmailExtractor

__all__ = ["EmailExtractor"]