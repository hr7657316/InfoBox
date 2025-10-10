"""
Unit tests for StorageManager
"""

import unittest
import tempfile
import shutil
import json
import csv
from pathlib import Path
from datetime import datetime

from pipeline.utils.storage import StorageManager


class TestStorageManager(unittest.TestCase):
    """Test cases for StorageManager class"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_manager = StorageManager(self.temp_dir)
        
        # Sample test data
        self.sample_data = [
            {
                'id': '1',
                'timestamp': '2025-09-30T10:00:00',
                'sender': 'test@example.com',
                'content': 'Test message 1'
            },
            {
                'id': '2',
                'timestamp': '2025-09-30T11:00:00',
                'sender': 'user@example.com',
                'content': 'Test message 2'
            }
        ]
        
        self.sample_media_content = b'fake_image_content_12345'
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_init(self):
        """Test StorageManager initialization"""
        self.assertTrue(Path(self.temp_dir).exists())
        self.assertEqual(str(self.storage_manager.base_path), self.temp_dir)
    
    def test_create_directory_structure(self):
        """Test directory structure creation"""
        source = 'whatsapp'
        date = '2025-09-30'
        
        result_path = self.storage_manager.create_directory_structure(source, date)
        
        # Check that the correct path is returned
        expected_path = str(Path(self.temp_dir) / source / date)
        self.assertEqual(result_path, expected_path)
        
        # Check that directories are created
        self.assertTrue(Path(result_path).exists())
        self.assertTrue(Path(result_path, 'media').exists())
        self.assertTrue(Path(result_path, 'data').exists())
    
    def test_save_json(self):
        """Test JSON file saving"""
        test_file = str(Path(self.temp_dir) / 'test.json')
        
        self.storage_manager.save_json(self.sample_data, test_file)
        
        # Verify file exists
        self.assertTrue(Path(test_file).exists())
        
        # Verify content
        with open(test_file, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
        
        self.assertEqual(loaded_data, self.sample_data)
    
    def test_save_json_creates_directories(self):
        """Test that save_json creates parent directories"""
        test_file = str(Path(self.temp_dir) / 'nested' / 'dir' / 'test.json')
        
        self.storage_manager.save_json(self.sample_data, test_file)
        
        self.assertTrue(Path(test_file).exists())
    
    def test_save_csv(self):
        """Test CSV file saving"""
        test_file = str(Path(self.temp_dir) / 'test.csv')
        
        self.storage_manager.save_csv(self.sample_data, test_file)
        
        # Verify file exists
        self.assertTrue(Path(test_file).exists())
        
        # Verify content
        with open(test_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            loaded_data = list(reader)
        
        self.assertEqual(len(loaded_data), len(self.sample_data))
        self.assertEqual(loaded_data[0]['id'], '1')
        self.assertEqual(loaded_data[1]['id'], '2')
    
    def test_save_csv_empty_data(self):
        """Test CSV saving with empty data"""
        test_file = str(Path(self.temp_dir) / 'empty.csv')
        
        self.storage_manager.save_csv([], test_file)
        
        # File should not be created for empty data
        self.assertFalse(Path(test_file).exists())
    
    def test_save_csv_creates_directories(self):
        """Test that save_csv creates parent directories"""
        test_file = str(Path(self.temp_dir) / 'nested' / 'dir' / 'test.csv')
        
        self.storage_manager.save_csv(self.sample_data, test_file)
        
        self.assertTrue(Path(test_file).exists())
    
    def test_save_media_file(self):
        """Test media file saving with unique naming"""
        media_dir = str(Path(self.temp_dir) / 'media')
        filename = 'test_image.jpg'
        
        result_path = self.storage_manager.save_media_file(
            self.sample_media_content, filename, media_dir
        )
        
        # Verify file exists
        self.assertTrue(Path(result_path).exists())
        
        # Verify content
        with open(result_path, 'rb') as f:
            saved_content = f.read()
        
        self.assertEqual(saved_content, self.sample_media_content)
        
        # Verify unique naming (should contain timestamp and hash)
        result_filename = Path(result_path).name
        self.assertIn('test_image', result_filename)
        self.assertTrue(result_filename.endswith('.jpg'))
        self.assertNotEqual(result_filename, filename)  # Should be unique
    
    def test_save_media_file_deduplication(self):
        """Test media file deduplication"""
        media_dir = str(Path(self.temp_dir) / 'media')
        filename = 'test_image.jpg'
        
        # Save the same file twice
        path1 = self.storage_manager.save_media_file(
            self.sample_media_content, filename, media_dir
        )
        path2 = self.storage_manager.save_media_file(
            self.sample_media_content, filename, media_dir
        )
        
        # Should return the same path (deduplication)
        self.assertEqual(path1, path2)
        
        # Should only have one file
        media_files = list(Path(media_dir).glob('*'))
        self.assertEqual(len(media_files), 1)
    
    def test_deduplicate_data_with_ids(self):
        """Test data deduplication using ID field"""
        existing_data = [
            {'id': '1', 'content': 'existing message 1'},
            {'id': '2', 'content': 'existing message 2'}
        ]
        
        new_data = [
            {'id': '1', 'content': 'duplicate message'},  # Duplicate
            {'id': '3', 'content': 'new message 3'},      # New
            {'id': '4', 'content': 'new message 4'}       # New
        ]
        
        result = self.storage_manager.deduplicate_data(new_data, existing_data)
        
        # Should only return new items
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['id'], '3')
        self.assertEqual(result[1]['id'], '4')
    
    def test_deduplicate_data_without_ids(self):
        """Test data deduplication using content hash"""
        existing_data = [
            {'content': 'existing message 1', 'sender': 'user1'},
            {'content': 'existing message 2', 'sender': 'user2'}
        ]
        
        new_data = [
            {'content': 'existing message 1', 'sender': 'user1'},  # Duplicate
            {'content': 'new message 3', 'sender': 'user3'},       # New
            {'content': 'new message 4', 'sender': 'user4'}        # New
        ]
        
        result = self.storage_manager.deduplicate_data(new_data, existing_data)
        
        # Should only return new items
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['content'], 'new message 3')
        self.assertEqual(result[1]['content'], 'new message 4')
    
    def test_deduplicate_data_empty_existing(self):
        """Test deduplication with empty existing data"""
        result = self.storage_manager.deduplicate_data(self.sample_data, [])
        
        # Should return all new data
        self.assertEqual(result, self.sample_data)
    
    def test_deduplicate_data_prevents_internal_duplicates(self):
        """Test that deduplication prevents duplicates within new data itself"""
        new_data = [
            {'id': '1', 'content': 'message 1'},
            {'id': '1', 'content': 'message 1'},  # Internal duplicate
            {'id': '2', 'content': 'message 2'}
        ]
        
        result = self.storage_manager.deduplicate_data(new_data, [])
        
        # Should only have 2 unique items
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['id'], '1')
        self.assertEqual(result[1]['id'], '2')
    
    def test_ensure_directory_exists(self):
        """Test directory creation utility"""
        test_path = str(Path(self.temp_dir) / 'nested' / 'test' / 'dir')
        
        result_path = self.storage_manager.ensure_directory_exists(test_path)
        
        self.assertTrue(result_path.exists())
        self.assertEqual(str(result_path), test_path)
    
    def test_load_existing_data_file_exists(self):
        """Test loading existing data from JSON file"""
        test_file = str(Path(self.temp_dir) / 'existing.json')
        
        # Create test file
        with open(test_file, 'w', encoding='utf-8') as f:
            json.dump(self.sample_data, f)
        
        result = self.storage_manager.load_existing_data(test_file)
        
        self.assertEqual(result, self.sample_data)
    
    def test_load_existing_data_file_not_exists(self):
        """Test loading data from non-existent file"""
        test_file = str(Path(self.temp_dir) / 'nonexistent.json')
        
        result = self.storage_manager.load_existing_data(test_file)
        
        self.assertEqual(result, [])
    
    def test_load_existing_data_invalid_json(self):
        """Test loading data from invalid JSON file"""
        test_file = str(Path(self.temp_dir) / 'invalid.json')
        
        # Create invalid JSON file
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write('invalid json content')
        
        result = self.storage_manager.load_existing_data(test_file)
        
        self.assertEqual(result, [])
    
    def test_get_storage_paths(self):
        """Test storage path generation"""
        source = 'email'
        date = '2025-09-30'
        
        paths = self.storage_manager.get_storage_paths(source, date)
        
        # Verify all expected paths are present
        expected_keys = ['base', 'data', 'media', 'json', 'csv']
        self.assertEqual(set(paths.keys()), set(expected_keys))
        
        # Verify path structure
        base_path = Path(self.temp_dir) / source / date
        self.assertEqual(paths['base'], str(base_path))
        self.assertEqual(paths['data'], str(base_path / 'data'))
        self.assertEqual(paths['media'], str(base_path / 'media'))
        self.assertEqual(paths['json'], str(base_path / 'data' / f'{source}_messages.json'))
        self.assertEqual(paths['csv'], str(base_path / 'data' / f'{source}_messages.csv'))
        
        # Verify directories are created
        self.assertTrue(Path(paths['base']).exists())
        self.assertTrue(Path(paths['data']).exists())
        self.assertTrue(Path(paths['media']).exists())


if __name__ == '__main__':
    unittest.main()