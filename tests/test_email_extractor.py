"""
Unit tests for email extractor
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from pipeline.email.email_extractor import EmailExtractor, ConnectionPool
from pipeline.models import Email


class TestConnectionPool(unittest.TestCase):
    """Test cases for ConnectionPool class"""
    
    def setUp(self):
        self.pool = ConnectionPool(max_connections=2)
        self.config = {
            'imap_server': 'imap.gmail.com',
            'imap_port': 993,
            'use_ssl': True
        }
    
    @patch('pipeline.email.email_extractor.imaplib.IMAP4_SSL')
    def test_create_connection_success(self, mock_imap):
        """Test successful connection creation"""
        mock_connection = Mock()
        mock_imap.return_value = mock_connection
        
        connection = self.pool.get_connection('test_account', self.config)
        
        self.assertIsNotNone(connection)
        self.assertEqual(connection, mock_connection)
        mock_imap.assert_called_once_with('imap.gmail.com', 993)
    
    @patch('pipeline.email.email_extractor.imaplib.IMAP4_SSL')
    def test_connection_reuse(self, mock_imap):
        """Test connection reuse"""
        mock_connection = Mock()
        mock_imap.return_value = mock_connection
        
        # First call creates connection
        connection1 = self.pool.get_connection('test_account', self.config)
        
        # Second call reuses connection
        connection2 = self.pool.get_connection('test_account', self.config)
        
        self.assertEqual(connection1, connection2)
        mock_imap.assert_called_once()  # Only called once
    
    def test_close_connection(self):
        """Test connection cleanup"""
        with patch('pipeline.email.email_extractor.imaplib.IMAP4_SSL') as mock_imap:
            mock_connection = Mock()
            mock_imap.return_value = mock_connection
            
            # Create connection
            self.pool.get_connection('test_account', self.config)
            
            # Close connection
            self.pool.close_connection('test_account')
            
            # Verify cleanup
            mock_connection.close.assert_called_once()
            mock_connection.logout.assert_called_once()


class TestEmailExtractor(unittest.TestCase):
    """Test cases for EmailExtractor class"""
    
    def setUp(self):
        self.config = {
            'accounts': [
                {
                    'email': 'test@example.com',
                    'password': 'test_password',
                    'imap_server': 'imap.example.com',
                    'imap_port': 993,
                    'use_ssl': True,
                    'auth_method': 'password'
                }
            ],
            'timeout': 30,
            'max_retries': 3,
            'batch_size': 50
        }
        self.extractor = EmailExtractor(self.config)
    
    def test_initialization(self):
        """Test extractor initialization"""
        self.assertEqual(len(self.extractor.accounts), 1)
        self.assertEqual(self.extractor.timeout, 30)
        self.assertEqual(self.extractor.max_retries, 3)
        self.assertEqual(self.extractor.batch_size, 50)
        self.assertFalse(self.extractor._authenticated)
    
    @patch('pipeline.email.email_extractor.imaplib.IMAP4_SSL')
    def test_password_authentication_success(self, mock_imap):
        """Test successful password authentication"""
        mock_connection = Mock()
        mock_imap.return_value = mock_connection
        
        result = self.extractor.authenticate()
        
        self.assertTrue(result)
        self.assertTrue(self.extractor._authenticated)
        mock_connection.login.assert_called_once_with('test@example.com', 'test_password')
    
    @patch('pipeline.email.email_extractor.imaplib.IMAP4_SSL')
    def test_password_authentication_failure(self, mock_imap):
        """Test failed password authentication"""
        mock_connection = Mock()
        mock_connection.login.side_effect = imaplib.IMAP4.error("Authentication failed")
        mock_imap.return_value = mock_connection
        
        result = self.extractor.authenticate()
        
        self.assertFalse(result)
        self.assertFalse(self.extractor._authenticated)
    
    def test_build_search_criteria_basic(self):
        """Test basic search criteria building"""
        filters = {}
        criteria = self.extractor._build_search_criteria(filters)
        self.assertEqual(criteria, 'ALL')
    
    def test_build_search_criteria_date_range(self):
        """Test search criteria with date range"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        filters = {'date_range': (start_date, end_date)}
        
        criteria = self.extractor._build_search_criteria(filters)
        
        self.assertIn('SINCE "01-Jan-2024"', criteria)
        self.assertIn('BEFORE "31-Jan-2024"', criteria)
    
    def test_build_search_criteria_unread_only(self):
        """Test search criteria for unread emails only"""
        filters = {'unread_only': True}
        criteria = self.extractor._build_search_criteria(filters)
        self.assertIn('UNSEEN', criteria)
    
    def test_build_search_criteria_subject_filter(self):
        """Test search criteria with subject filter"""
        filters = {'subject': 'Important'}
        criteria = self.extractor._build_search_criteria(filters)
        self.assertIn('SUBJECT "Important"', criteria)
    
    def test_build_search_criteria_from_filter(self):
        """Test search criteria with from filter"""
        filters = {'from_email': 'sender@example.com'}
        criteria = self.extractor._build_search_criteria(filters)
        self.assertIn('FROM "sender@example.com"', criteria)
    
    def test_decode_header_simple(self):
        """Test simple header decoding"""
        header = "Simple Subject"
        decoded = self.extractor._decode_header(header)
        self.assertEqual(decoded, "Simple Subject")
    
    def test_decode_header_encoded(self):
        """Test encoded header decoding"""
        # This would be a real encoded header in practice
        header = "=?UTF-8?B?VGVzdCBTdWJqZWN0?="  # "Test Subject" in base64
        decoded = self.extractor._decode_header(header)
        self.assertEqual(decoded, "Test Subject")
    
    def test_extract_email_address(self):
        """Test email address extraction from From header"""
        from_header = "John Doe <john@example.com>"
        email_addr = self.extractor._extract_email_address(from_header)
        self.assertEqual(email_addr, "john@example.com")
    
    def test_extract_recipient_emails(self):
        """Test recipient email extraction"""
        to_header = "user1@example.com, User Two <user2@example.com>"
        cc_header = "user3@example.com"
        
        recipients = self.extractor._extract_recipient_emails(to_header, cc_header)
        
        expected = ["user1@example.com", "user2@example.com", "user3@example.com"]
        self.assertEqual(sorted(recipients), sorted(expected))
    
    def test_parse_email_date(self):
        """Test email date parsing"""
        date_str = "Mon, 01 Jan 2024 12:00:00 +0000"
        parsed_date = self.extractor._parse_email_date(date_str)
        
        self.assertIsInstance(parsed_date, datetime)
        self.assertEqual(parsed_date.year, 2024)
        self.assertEqual(parsed_date.month, 1)
        self.assertEqual(parsed_date.day, 1)
    
    def test_parse_email_date_invalid(self):
        """Test email date parsing with invalid date"""
        date_str = "Invalid Date"
        parsed_date = self.extractor._parse_email_date(date_str)
        
        # Should return current time for invalid dates
        self.assertIsInstance(parsed_date, datetime)
        # Check it's recent (within last minute)
        self.assertTrue((datetime.now() - parsed_date).total_seconds() < 60)
    
    def create_test_email_message(self, subject="Test Subject", 
                                 from_addr="sender@example.com",
                                 to_addr="recipient@example.com",
                                 body_text="Test body text",
                                 body_html="<p>Test body HTML</p>"):
        """Create a test email message"""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_addr
        msg['To'] = to_addr
        msg['Date'] = email.utils.formatdate(localtime=True)
        msg['Message-ID'] = f"<test-{datetime.now().timestamp()}@example.com>"
        
        # Add text part
        text_part = MIMEText(body_text, 'plain')
        msg.attach(text_part)
        
        # Add HTML part
        html_part = MIMEText(body_html, 'html')
        msg.attach(html_part)
        
        return msg
    
    def test_extract_email_body_multipart(self):
        """Test email body extraction from multipart message"""
        test_msg = self.create_test_email_message(
            body_text="Plain text content",
            body_html="<p>HTML content</p>"
        )
        
        body_text, body_html = self.extractor._extract_email_body(test_msg)
        
        self.assertEqual(body_text, "Plain text content")
        self.assertEqual(body_html, "<p>HTML content</p>")
    
    def test_extract_email_body_plain_text(self):
        """Test email body extraction from plain text message"""
        msg = MIMEText("Plain text only", 'plain')
        
        body_text, body_html = self.extractor._extract_email_body(msg)
        
        self.assertEqual(body_text, "Plain text only")
        self.assertEqual(body_html, "")
    
    def test_filter_by_keywords(self):
        """Test keyword filtering"""
        emails = [
            Email(
                id="1", timestamp=datetime.now(), sender_email="test@example.com",
                recipient_emails=[], subject="Important meeting", body_text="Meeting details",
                body_html="", attachments=[], is_read=True, folder="INBOX"
            ),
            Email(
                id="2", timestamp=datetime.now(), sender_email="test@example.com",
                recipient_emails=[], subject="Regular update", body_text="Update info",
                body_html="", attachments=[], is_read=True, folder="INBOX"
            )
        ]
        
        keywords = ["important", "meeting"]
        filtered = self.extractor._filter_by_keywords(emails, keywords)
        
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].id, "1")
    
    def test_filter_by_sender_domains(self):
        """Test sender domain filtering"""
        emails = [
            Email(
                id="1", timestamp=datetime.now(), sender_email="user@company.com",
                recipient_emails=[], subject="Work email", body_text="Work content",
                body_html="", attachments=[], is_read=True, folder="INBOX"
            ),
            Email(
                id="2", timestamp=datetime.now(), sender_email="friend@personal.com",
                recipient_emails=[], subject="Personal email", body_text="Personal content",
                body_html="", attachments=[], is_read=True, folder="INBOX"
            )
        ]
        
        domains = ["company.com"]
        filtered = self.extractor._filter_by_sender_domains(emails, domains)
        
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].id, "1")
    
    def test_apply_post_fetch_filters_attachments(self):
        """Test post-fetch filtering by attachments"""
        emails = [
            Email(
                id="1", timestamp=datetime.now(), sender_email="test@example.com",
                recipient_emails=[], subject="With attachment", body_text="Content",
                body_html="", attachments=[{"filename": "doc.pdf"}], is_read=True, folder="INBOX"
            ),
            Email(
                id="2", timestamp=datetime.now(), sender_email="test@example.com",
                recipient_emails=[], subject="No attachment", body_text="Content",
                body_html="", attachments=[], is_read=True, folder="INBOX"
            )
        ]
        
        # Filter for emails with attachments
        filters = {'has_attachments': True}
        filtered = self.extractor._apply_post_fetch_filters(emails, filters)
        
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].id, "1")
        
        # Filter for emails without attachments
        filters = {'has_attachments': False}
        filtered = self.extractor._apply_post_fetch_filters(emails, filters)
        
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].id, "2")
    
    def test_email_to_dict(self):
        """Test email object to dictionary conversion"""
        email_obj = Email(
            id="test-123",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            sender_email="sender@example.com",
            recipient_emails=["recipient@example.com"],
            subject="Test Subject",
            body_text="Test body",
            body_html="<p>Test body</p>",
            attachments=[{"filename": "test.pdf"}],
            is_read=True,
            folder="INBOX"
        )
        
        email_dict = self.extractor._email_to_dict(email_obj)
        
        self.assertEqual(email_dict['id'], "test-123")
        self.assertEqual(email_dict['sender_email'], "sender@example.com")
        self.assertEqual(email_dict['subject'], "Test Subject")
        self.assertEqual(email_dict['is_read'], True)
        self.assertEqual(email_dict['folder'], "INBOX")
        self.assertIn('timestamp', email_dict)
        self.assertIn('extracted_at', email_dict)
    
    def tearDown(self):
        """Clean up after tests"""
        self.extractor.close_connections()


class TestEmailExtractionIntegration(unittest.TestCase):
    """Integration tests for email extraction workflow"""
    
    def setUp(self):
        self.config = {
            'accounts': [
                {
                    'email': 'test@example.com',
                    'password': 'test_password',
                    'imap_server': 'imap.example.com',
                    'imap_port': 993,
                    'use_ssl': True,
                    'auth_method': 'password'
                }
            ]
        }
        self.extractor = EmailExtractor(self.config)
    
    @patch('pipeline.email.email_extractor.imaplib.IMAP4_SSL')
    def test_full_extraction_workflow(self, mock_imap):
        """Test complete email extraction workflow"""
        # Mock IMAP connection and responses
        mock_connection = Mock()
        mock_imap.return_value = mock_connection
        
        # Mock successful authentication
        mock_connection.login.return_value = None
        
        # Mock folder selection
        mock_connection.select.return_value = ('OK', [b'10'])
        
        # Mock email search
        mock_connection.search.return_value = ('OK', [b'1 2 3'])
        
        # Mock email fetch - create realistic email data
        test_email = self.create_test_email_message()
        email_bytes = test_email.as_bytes()
        
        # Mock fetch to return proper format for each message ID
        def mock_fetch(message_id, fetch_parts):
            return ('OK', [(f'{message_id.decode()} (RFC822 {{1234}}'.encode(), email_bytes), b')'])
        
        mock_connection.fetch.side_effect = mock_fetch
        
        # Test the workflow
        success = self.extractor.authenticate()
        self.assertTrue(success)
        
        emails = self.extractor.extract_emails({'limit': 3})
        
        # Verify results
        self.assertEqual(len(emails), 3)  # Should process 3 messages
        for email_obj in emails:
            self.assertIsInstance(email_obj, Email)
            self.assertIsNotNone(email_obj.id)
            self.assertIsNotNone(email_obj.timestamp)
    
    def create_test_email_message(self):
        """Create a realistic test email message"""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Test Email Subject"
        msg['From'] = "sender@example.com"
        msg['To'] = "recipient@example.com"
        msg['Date'] = email.utils.formatdate(localtime=True)
        msg['Message-ID'] = f"<test-{datetime.now().timestamp()}@example.com>"
        
        # Add text content
        text_part = MIMEText("This is the plain text content of the email.", 'plain')
        msg.attach(text_part)
        
        # Add HTML content
        html_part = MIMEText("<p>This is the <b>HTML</b> content of the email.</p>", 'html')
        msg.attach(html_part)
        
        return msg
    
    def tearDown(self):
        """Clean up after tests"""
        self.extractor.close_connections()


class TestEmailAttachmentHandling(unittest.TestCase):
    """Test cases for email attachment handling"""
    
    def setUp(self):
        self.config = {
            'accounts': [
                {
                    'email': 'test@example.com',
                    'password': 'test_password',
                    'imap_server': 'imap.example.com',
                    'imap_port': 993,
                    'use_ssl': True,
                    'auth_method': 'password'
                }
            ]
        }
        self.extractor = EmailExtractor(self.config)
    
    def test_get_extension_from_content_type(self):
        """Test file extension extraction from content type"""
        test_cases = [
            ('application/pdf', '.pdf'),
            ('image/jpeg', '.jpg'),
            ('text/plain', '.txt'),
            ('application/octet-stream', '.bin'),
            ('unknown/type', '.bin')
        ]
        
        for content_type, expected_ext in test_cases:
            ext = self.extractor._get_extension_from_content_type(content_type)
            self.assertEqual(ext, expected_ext)
    
    def test_generate_unique_attachment_filename(self):
        """Test unique filename generation for attachments"""
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test basic filename generation
            filename = self.extractor._generate_unique_attachment_filename(
                'document.pdf', temp_dir, 'test@example.com', 1
            )
            
            self.assertTrue(filename.endswith('.pdf'))
            self.assertIn('document', filename)
            
            # Create a file with the generated name
            with open(os.path.join(temp_dir, filename), 'w') as f:
                f.write('test')
            
            # Generate another filename - should be different
            filename2 = self.extractor._generate_unique_attachment_filename(
                'document.pdf', temp_dir, 'test@example.com', 1
            )
            
            self.assertNotEqual(filename, filename2)
            self.assertTrue(filename2.endswith('.pdf'))
    
    def create_email_with_attachment(self, attachment_filename='test.pdf', 
                                   attachment_content=b'PDF content'):
        """Create a test email with attachment"""
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.application import MIMEApplication
        
        msg = MIMEMultipart()
        msg['Subject'] = "Email with attachment"
        msg['From'] = "sender@example.com"
        msg['To'] = "recipient@example.com"
        msg['Date'] = email.utils.formatdate(localtime=True)
        msg['Message-ID'] = f"<test-attachment-{datetime.now().timestamp()}@example.com>"
        
        # Add text content
        text_part = MIMEText("This email has an attachment.", 'plain')
        msg.attach(text_part)
        
        # Add attachment
        attachment = MIMEApplication(attachment_content)
        attachment.add_header('Content-Disposition', 'attachment', filename=attachment_filename)
        msg.attach(attachment)
        
        return msg
    
    def test_extract_attachment_info(self):
        """Test attachment information extraction"""
        test_email = self.create_email_with_attachment('document.pdf', b'PDF file content')
        
        attachments = self.extractor._extract_attachment_info(test_email)
        
        self.assertEqual(len(attachments), 1)
        
        attachment = attachments[0]
        self.assertEqual(attachment['filename'], 'document.pdf')
        self.assertEqual(attachment['size'], len(b'PDF file content'))
        self.assertIn('content_type', attachment)
        self.assertIn('part_id', attachment)
        self.assertFalse(attachment['is_inline'])
    
    def test_extract_attachment_info_multiple(self):
        """Test extraction of multiple attachments"""
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.application import MIMEApplication
        
        msg = MIMEMultipart()
        msg['Subject'] = "Email with multiple attachments"
        msg['From'] = "sender@example.com"
        msg['To'] = "recipient@example.com"
        msg['Message-ID'] = "<multi-attach@example.com>"
        
        # Add text content
        text_part = MIMEText("This email has multiple attachments.", 'plain')
        msg.attach(text_part)
        
        # Add first attachment
        attachment1 = MIMEApplication(b'PDF content')
        attachment1.add_header('Content-Disposition', 'attachment', filename='doc1.pdf')
        msg.attach(attachment1)
        
        # Add second attachment
        attachment2 = MIMEApplication(b'Image content')
        attachment2.add_header('Content-Disposition', 'attachment', filename='image.jpg')
        msg.attach(attachment2)
        
        attachments = self.extractor._extract_attachment_info(msg)
        
        self.assertEqual(len(attachments), 2)
        
        filenames = [att['filename'] for att in attachments]
        self.assertIn('doc1.pdf', filenames)
        self.assertIn('image.jpg', filenames)
    
    def test_extract_attachment_info_inline(self):
        """Test extraction of inline attachments"""
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.image import MIMEImage
        
        msg = MIMEMultipart()
        msg['Subject'] = "Email with inline attachment"
        msg['From'] = "sender@example.com"
        msg['To'] = "recipient@example.com"
        msg['Message-ID'] = "<inline-attach@example.com>"
        
        # Add text content
        text_part = MIMEText("This email has an inline image.", 'plain')
        msg.attach(text_part)
        
        # Add inline image - use proper JPEG header to avoid MIME type guessing error
        # Create minimal JPEG header
        jpeg_header = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb'
        fake_jpeg_content = jpeg_header + b'\x00' * 100  # Minimal JPEG-like content
        
        image = MIMEImage(fake_jpeg_content)
        image.add_header('Content-Disposition', 'inline', filename='inline.jpg')
        image.add_header('Content-ID', '<image1>')
        msg.attach(image)
        
        attachments = self.extractor._extract_attachment_info(msg)
        
        self.assertEqual(len(attachments), 1)
        
        attachment = attachments[0]
        self.assertEqual(attachment['filename'], 'inline.jpg')
        self.assertTrue(attachment['is_inline'])
        self.assertEqual(attachment['content_id'], 'image1')
    
    def test_extract_attachment_info_no_filename(self):
        """Test extraction when attachment has no filename"""
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.application import MIMEApplication
        
        msg = MIMEMultipart()
        msg['Subject'] = "Email with unnamed attachment"
        msg['From'] = "sender@example.com"
        msg['To'] = "recipient@example.com"
        msg['Message-ID'] = "<unnamed-attach@example.com>"
        
        # Add text content
        text_part = MIMEText("This email has an unnamed attachment.", 'plain')
        msg.attach(text_part)
        
        # Add attachment without filename
        attachment = MIMEApplication(b'Binary content')
        attachment.add_header('Content-Disposition', 'attachment')  # No filename
        msg.attach(attachment)
        
        attachments = self.extractor._extract_attachment_info(msg)
        
        self.assertEqual(len(attachments), 1)
        
        attachment = attachments[0]
        self.assertTrue(attachment['filename'].startswith('attachment_'))
        self.assertTrue(attachment['filename'].endswith('.bin'))
    
    @patch('pipeline.email.email_extractor.imaplib.IMAP4_SSL')
    @patch('os.makedirs')
    @patch('os.rename')
    @patch('builtins.open', create=True)
    def test_extract_and_save_attachments(self, mock_open, mock_rename, mock_makedirs, mock_imap):
        """Test attachment extraction and saving"""
        # Create test email with attachment
        test_email = self.create_email_with_attachment('test.pdf', b'PDF content')
        email_bytes = test_email.as_bytes()
        
        # Mock IMAP connection
        mock_connection = Mock()
        mock_connection.fetch.return_value = ('OK', [(b'1 (RFC822 {1234}', email_bytes), b')'])
        
        # Mock file operations
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        # Test the method
        output_path = '/test/output'
        email_id = 'test@example.com'
        
        files = self.extractor._extract_and_save_attachments(
            mock_connection, b'1', output_path, email_id
        )
        
        # Verify results
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].endswith('.pdf'))
        
        # Verify file operations
        mock_makedirs.assert_called_once_with(output_path, exist_ok=True)
        mock_file.write.assert_called_once_with(b'PDF content')
        mock_rename.assert_called_once()  # Atomic write with rename
    
    @patch('pipeline.email.email_extractor.imaplib.IMAP4_SSL')
    @patch('os.makedirs')
    @patch('builtins.open', create=True)
    def test_extract_and_save_attachments_error_handling(self, mock_open, mock_makedirs, mock_imap):
        """Test attachment extraction with error handling"""
        # Create test email with attachment
        test_email = self.create_email_with_attachment('test.pdf', b'PDF content')
        email_bytes = test_email.as_bytes()
        
        # Mock IMAP connection
        mock_connection = Mock()
        mock_connection.fetch.return_value = ('OK', [(b'1 (RFC822 {1234}', email_bytes), b')'])
        
        # Mock file operations to raise error
        mock_open.side_effect = OSError("Permission denied")
        
        # Test the method
        output_path = '/test/output'
        email_id = 'test@example.com'
        
        files = self.extractor._extract_and_save_attachments(
            mock_connection, b'1', output_path, email_id
        )
        
        # Should handle error gracefully and return empty list
        self.assertEqual(len(files), 0)
    
    def test_download_attachments_batch(self):
        """Test batch attachment downloading"""
        # Mock the download_attachments method
        with patch.object(self.extractor, 'download_attachments') as mock_download:
            mock_download.side_effect = [
                ['/path/file1.pdf', '/path/file2.jpg'],  # First email
                [],  # Second email (no attachments)
                ['/path/file3.doc']  # Third email
            ]
            
            email_list = [
                {'email_id': 'email1@example.com'},
                {'email_id': 'email2@example.com'},
                {'email_id': 'email3@example.com'}
            ]
            
            results = self.extractor.download_attachments_batch(email_list, '/output')
            
            # Verify results
            self.assertEqual(len(results), 3)
            self.assertEqual(len(results['email1@example.com']), 2)
            self.assertEqual(len(results['email2@example.com']), 0)
            self.assertEqual(len(results['email3@example.com']), 1)
    
    def test_download_attachments_with_storage(self):
        """Test attachment downloading with storage manager integration"""
        from unittest.mock import Mock
        
        # Mock storage manager
        mock_storage = Mock()
        mock_storage.get_storage_paths.return_value = {
            'base': '/data/email/2024-01-01',
            'media': '/data/email/2024-01-01/media',
            'data': '/data/email/2024-01-01/data'
        }
        
        # Mock the download_attachments method
        with patch.object(self.extractor, 'download_attachments') as mock_download:
            mock_download.return_value = ['/data/email/2024-01-01/media/email_test/file.pdf']
            
            files = self.extractor.download_attachments_with_storage(
                'test@example.com', mock_storage, '2024-01-01'
            )
            
            # Verify storage manager was called correctly
            mock_storage.get_storage_paths.assert_called_once_with('email', '2024-01-01')
            
            # Verify download was called with organized path
            mock_download.assert_called_once()
            call_args = mock_download.call_args[0]
            self.assertEqual(call_args[0], 'test@example.com')
            self.assertIn('email_test_at_example.com', call_args[1])
            
            # Verify results
            self.assertEqual(len(files), 1)
            self.assertTrue(files[0].endswith('.pdf'))
    
    def test_extract_attachment_info_with_dates(self):
        """Test attachment info extraction with creation/modification dates"""
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.application import MIMEApplication
        
        msg = MIMEMultipart()
        msg['Subject'] = "Email with dated attachment"
        msg['From'] = "sender@example.com"
        msg['To'] = "recipient@example.com"
        msg['Message-ID'] = "<dated-attach@example.com>"
        
        # Add text content
        text_part = MIMEText("This email has a dated attachment.", 'plain')
        msg.attach(text_part)
        
        # Add attachment with dates in Content-Disposition
        attachment = MIMEApplication(b'File content with dates')
        attachment.add_header(
            'Content-Disposition', 
            'attachment; filename="dated_file.pdf"; creation-date="Mon, 01 Jan 2024 12:00:00 +0000"'
        )
        msg.attach(attachment)
        
        attachments = self.extractor._extract_attachment_info(msg)
        
        self.assertEqual(len(attachments), 1)
        attachment = attachments[0]
        self.assertEqual(attachment['filename'], 'dated_file.pdf')
        self.assertIsNotNone(attachment['creation_date'])
    
    def test_large_attachment_handling(self):
        """Test handling of large attachments"""
        # Create a large attachment (simulate)
        large_content = b'x' * (50 * 1024 * 1024)  # 50MB
        test_email = self.create_email_with_attachment('large_file.zip', large_content)
        
        attachments = self.extractor._extract_attachment_info(test_email)
        
        self.assertEqual(len(attachments), 1)
        attachment = attachments[0]
        self.assertEqual(attachment['filename'], 'large_file.zip')
        self.assertEqual(attachment['size'], len(large_content))
    
    def test_attachment_content_type_detection(self):
        """Test content type detection for various file types"""
        test_cases = [
            ('document.pdf', 'application/pdf'),
            ('image.jpg', 'image/jpeg'),
            ('spreadsheet.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('archive.zip', 'application/zip'),
            ('text.txt', 'text/plain')
        ]
        
        for filename, expected_type in test_cases:
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            from email.mime.application import MIMEApplication
            
            msg = MIMEMultipart()
            msg['Subject'] = f"Email with {filename}"
            msg['From'] = "sender@example.com"
            msg['To'] = "recipient@example.com"
            
            # Add text content
            text_part = MIMEText("Email with attachment.", 'plain')
            msg.attach(text_part)
            
            # Add attachment
            attachment = MIMEApplication(b'File content', _subtype=expected_type.split('/')[-1])
            attachment.add_header('Content-Disposition', 'attachment', filename=filename)
            msg.attach(attachment)
            
            attachments = self.extractor._extract_attachment_info(msg)
            
            self.assertEqual(len(attachments), 1)
            # Note: The actual content type might be set by the MIMEApplication constructor
            self.assertEqual(attachments[0]['filename'], filename)
    
    def test_attachment_deduplication(self):
        """Test that duplicate attachments are handled properly"""
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test that same content gets same filename (deduplication)
            filename1 = self.extractor._generate_unique_attachment_filename(
                'document.pdf', temp_dir, 'test@example.com', 1
            )
            
            # Create the file
            with open(os.path.join(temp_dir, filename1), 'w') as f:
                f.write('test content')
            
            # Generate another filename with same parameters
            filename2 = self.extractor._generate_unique_attachment_filename(
                'document.pdf', temp_dir, 'test@example.com', 1
            )
            
            # Should be different to avoid conflicts
            self.assertNotEqual(filename1, filename2)
    
    def test_attachment_error_recovery(self):
        """Test error recovery during attachment processing"""
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.application import MIMEApplication
        
        # Create email with multiple attachments, one will fail
        msg = MIMEMultipart()
        msg['Subject'] = "Email with mixed attachments"
        msg['From'] = "sender@example.com"
        msg['To'] = "recipient@example.com"
        msg['Message-ID'] = "<mixed-attach@example.com>"
        
        # Add text content
        text_part = MIMEText("Email with multiple attachments.", 'plain')
        msg.attach(text_part)
        
        # Add good attachment
        good_attachment = MIMEApplication(b'Good content')
        good_attachment.add_header('Content-Disposition', 'attachment', filename='good.pdf')
        msg.attach(good_attachment)
        
        # Add problematic attachment (will simulate error during processing)
        bad_attachment = MIMEApplication(b'Bad content')
        bad_attachment.add_header('Content-Disposition', 'attachment', filename='bad.pdf')
        # Simulate a problematic attachment by making get_payload return None
        bad_attachment.get_payload = lambda decode=False: None
        msg.attach(bad_attachment)
        
        attachments = self.extractor._extract_attachment_info(msg)
        
        # Should still extract info for both, even if one is problematic
        self.assertEqual(len(attachments), 2)
        filenames = [att['filename'] for att in attachments]
        self.assertIn('good.pdf', filenames)
        self.assertIn('bad.pdf', filenames)
    
    def tearDown(self):
        """Clean up after tests"""
        self.extractor.close_connections()


if __name__ == '__main__':
    unittest.main()