"""
Data Extraction Pipeline

A modular Python application for extracting messages and attachments 
from WhatsApp and email sources with organized storage and scheduling.
"""

__version__ = "1.0.0"
__author__ = "Data Extraction Pipeline"

from .main import PipelineOrchestrator

__all__ = ["PipelineOrchestrator"]