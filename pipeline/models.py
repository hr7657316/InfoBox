"""
Core data models for the extraction pipeline
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod


@dataclass
class WhatsAppMessage:
    """Data model for WhatsApp messages"""
    id: str
    timestamp: datetime
    sender_phone: str
    message_content: str
    message_type: str  # text, image, audio, video, document
    media_url: Optional[str] = None
    media_filename: Optional[str] = None
    media_size: Optional[int] = None
    extracted_at: datetime = None
    
    def __post_init__(self):
        if self.extracted_at is None:
            self.extracted_at = datetime.now()


@dataclass
class Email:
    """Data model for email messages"""
    id: str
    timestamp: datetime
    sender_email: str
    recipient_emails: List[str]
    subject: str
    body_text: str
    body_html: str
    attachments: List[Dict[str, Any]]  # filename, size, content_type
    is_read: bool
    folder: str
    extracted_at: datetime = None
    
    def __post_init__(self):
        if self.extracted_at is None:
            self.extracted_at = datetime.now()


@dataclass
class ExtractionResult:
    """Result model for extraction operations"""
    source: str
    success: bool
    messages_count: int
    media_count: int
    errors: List[str]
    execution_time: float
    output_paths: Dict[str, str]


class BaseExtractor(ABC):
    """Abstract base class for all data extractors"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._authenticated = False
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the data source"""
        pass
    
    @abstractmethod
    def extract_data(self, **kwargs) -> List[Dict[str, Any]]:
        """Extract data from the source"""
        pass
    
    @abstractmethod
    def save_data(self, data: List[Dict[str, Any]], output_path: str) -> None:
        """Save extracted data to storage"""
        pass
    
    @property
    def is_authenticated(self) -> bool:
        """Check if extractor is authenticated"""
        return self._authenticated