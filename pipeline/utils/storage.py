"""
Storage management for the extraction pipeline
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import json
import csv
import hashlib
import os
from datetime import datetime


class StorageManager:
    """Manage data storage in multiple formats with organized directory structure"""
    
    def __init__(self, base_path: str = "data"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
    
    def create_directory_structure(self, source: str, date: str) -> str:
        """
        Create organized directory structure for data storage
        
        Args:
            source: Data source name (whatsapp, email)
            date: Date string for organization (YYYY-MM-DD)
            
        Returns:
            str: Path to created directory
        """
        # Create source-specific directory with date organization
        source_dir = self.base_path / source / date
        source_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for different data types
        (source_dir / "media").mkdir(exist_ok=True)
        (source_dir / "data").mkdir(exist_ok=True)
        
        return str(source_dir)
    
    def save_json(self, data: List[Dict[str, Any]], filepath: str) -> None:
        """
        Save data in JSON format
        
        Args:
            data: List of data dictionaries
            filepath: Path to save JSON file
        """
        filepath_obj = Path(filepath)
        filepath_obj.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath_obj, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    def save_csv(self, data: List[Dict[str, Any]], filepath: str) -> None:
        """
        Save data in CSV format
        
        Args:
            data: List of data dictionaries
            filepath: Path to save CSV file
        """
        if not data:
            return
            
        filepath_obj = Path(filepath)
        filepath_obj.parent.mkdir(parents=True, exist_ok=True)
        
        # Get all unique keys from all dictionaries for CSV headers
        fieldnames = set()
        for item in data:
            fieldnames.update(item.keys())
        fieldnames = sorted(list(fieldnames))
        
        with open(filepath_obj, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
    
    def save_media_file(self, content: bytes, filename: str, media_path: str) -> str:
        """
        Save media file with unique naming
        
        Args:
            content: File content as bytes
            filename: Original filename
            media_path: Directory to save media
            
        Returns:
            str: Path to saved file
        """
        media_dir = Path(media_path)
        media_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename using content hash and timestamp
        content_hash = hashlib.md5(content).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Extract file extension
        file_ext = Path(filename).suffix
        base_name = Path(filename).stem
        
        # Create unique filename
        unique_filename = f"{base_name}_{timestamp}_{content_hash}{file_ext}"
        file_path = media_dir / unique_filename
        
        # Check if file already exists (deduplication)
        if file_path.exists():
            with open(file_path, 'rb') as existing_file:
                if existing_file.read() == content:
                    return str(file_path)  # File already exists with same content
        
        # Save the file
        with open(file_path, 'wb') as f:
            f.write(content)
            
        return str(file_path)
    
    def deduplicate_data(self, new_data: List[Dict[str, Any]], existing_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate entries from new data
        
        Args:
            new_data: New data to check for duplicates
            existing_data: Existing data to compare against
            
        Returns:
            List of deduplicated data
        """
        # Create a set of existing item identifiers for fast lookup
        # Use 'id' field if available, otherwise use a hash of the entire record
        existing_ids = set()
        for item in existing_data:
            if 'id' in item:
                existing_ids.add(item['id'])
            else:
                # Create hash from sorted key-value pairs for consistent comparison
                item_str = json.dumps(item, sort_keys=True, default=str)
                existing_ids.add(hashlib.md5(item_str.encode()).hexdigest())
        
        # Filter out duplicates from new data (both against existing and internal duplicates)
        deduplicated = []
        seen_ids = existing_ids.copy()  # Start with existing IDs
        
        for item in new_data:
            if 'id' in item:
                item_id = item['id']
            else:
                item_str = json.dumps(item, sort_keys=True, default=str)
                item_id = hashlib.md5(item_str.encode()).hexdigest()
                
            if item_id not in seen_ids:
                deduplicated.append(item)
                seen_ids.add(item_id)  # Prevent duplicates within new_data itself
                
        return deduplicated
    
    def ensure_directory_exists(self, path: str) -> Path:
        """
        Ensure directory exists, create if necessary
        
        Args:
            path: Directory path
            
        Returns:
            Path object for the directory
        """
        dir_path = Path(path)
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
    
    def load_existing_data(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Load existing data from JSON file for deduplication
        
        Args:
            filepath: Path to existing JSON file
            
        Returns:
            List of existing data dictionaries, empty list if file doesn't exist
        """
        filepath_obj = Path(filepath)
        if not filepath_obj.exists():
            return []
            
        try:
            with open(filepath_obj, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    
    def get_storage_paths(self, source: str, date: str) -> Dict[str, str]:
        """
        Get standardized storage paths for a source and date
        
        Args:
            source: Data source name (whatsapp, email)
            date: Date string for organization (YYYY-MM-DD)
            
        Returns:
            Dictionary with paths for different data types
        """
        base_dir = self.create_directory_structure(source, date)
        
        return {
            'base': base_dir,
            'data': str(Path(base_dir) / 'data'),
            'media': str(Path(base_dir) / 'media'),
            'json': str(Path(base_dir) / 'data' / f'{source}_messages.json'),
            'csv': str(Path(base_dir) / 'data' / f'{source}_messages.csv')
        }
    
    def get_media_directory(self, source: str, date: str = None) -> str:
        """
        Get media directory for a specific source
        
        Args:
            source: Data source name (whatsapp, email)
            date: Date string for organization (defaults to today)
            
        Returns:
            Path to media directory
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        paths = self.get_storage_paths(source, date)
        return paths['media']
    
    def save_whatsapp_data(self, messages: List[Any]) -> Dict[str, str]:
        """
        Save WhatsApp messages data in both JSON and CSV formats
        
        Args:
            messages: List of WhatsAppMessage objects
            
        Returns:
            Dictionary with output file paths
        """
        date = datetime.now().strftime('%Y-%m-%d')
        paths = self.get_storage_paths('whatsapp', date)
        
        # Convert messages to dictionaries
        message_dicts = []
        for msg in messages:
            if hasattr(msg, '__dict__'):
                msg_dict = msg.__dict__.copy()
            else:
                msg_dict = dict(msg)
            
            # Convert datetime objects to strings for JSON serialization
            for key, value in msg_dict.items():
                if isinstance(value, datetime):
                    msg_dict[key] = value.isoformat()
            
            message_dicts.append(msg_dict)
        
        # Load existing data for deduplication
        existing_data = self.load_existing_data(paths['json'])
        
        # Deduplicate
        deduplicated_data = self.deduplicate_data(message_dicts, existing_data)
        
        # Combine with existing data
        all_data = existing_data + deduplicated_data
        
        # Save in both formats
        self.save_json(all_data, paths['json'])
        self.save_csv(all_data, paths['csv'])
        
        return {
            'json': paths['json'],
            'csv': paths['csv'],
            'media_dir': paths['media']
        }
    
    def save_email_data(self, emails: List[Any]) -> Dict[str, str]:
        """
        Save email data in both JSON and CSV formats
        
        Args:
            emails: List of Email objects
            
        Returns:
            Dictionary with output file paths
        """
        date = datetime.now().strftime('%Y-%m-%d')
        paths = self.get_storage_paths('email', date)
        
        # Convert emails to dictionaries
        email_dicts = []
        for email_obj in emails:
            if hasattr(email_obj, '__dict__'):
                email_dict = email_obj.__dict__.copy()
            else:
                email_dict = dict(email_obj)
            
            # Convert datetime objects to strings for JSON serialization
            for key, value in email_dict.items():
                if isinstance(value, datetime):
                    email_dict[key] = value.isoformat()
            
            email_dicts.append(email_dict)
        
        # Load existing data for deduplication
        existing_data = self.load_existing_data(paths['json'])
        
        # Deduplicate
        deduplicated_data = self.deduplicate_data(email_dicts, existing_data)
        
        # Combine with existing data
        all_data = existing_data + deduplicated_data
        
        # Save in both formats
        self.save_json(all_data, paths['json'])
        self.save_csv(all_data, paths['csv'])
        
        return {
            'json': paths['json'],
            'csv': paths['csv'],
            'media_dir': paths['media']
        }