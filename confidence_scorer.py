import json
import re
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from difflib import SequenceMatcher
import fitz  # PyMuPDF for PDF text extraction

class ConfidenceScorer:
    """
    Automatic confidence scoring system that compares original document content
    with processed/extracted content to calculate accuracy scores.
    """
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            lowercase=True,
            ngram_range=(1, 2),
            max_features=1000
        )
    
    def extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF file"""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return self.clean_text(text)
        except Exception as e:
            print(f"Error extracting PDF text: {e}")
            return ""
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text for comparison"""
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        # Remove special characters but keep alphanumeric and basic punctuation
        text = re.sub(r'[^\w\s.,!?-]', '', text)
        return text.lower()
    
    def calculate_text_similarity(self, original_text: str, processed_text: str) -> float:
        """Calculate similarity between original and processed text using TF-IDF cosine similarity"""
        if not original_text or not processed_text:
            return 0.0
        
        try:
            # Prepare texts
            texts = [self.clean_text(original_text), self.clean_text(processed_text)]
            
            # Calculate TF-IDF vectors
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            
            # Calculate cosine similarity
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            return float(similarity)
        except Exception as e:
            print(f"Error calculating similarity: {e}")
            return 0.0
    
    def calculate_sequence_similarity(self, original_text: str, processed_text: str) -> float:
        """Calculate sequence similarity using difflib"""
        try:
            matcher = SequenceMatcher(None, 
                                    self.clean_text(original_text), 
                                    self.clean_text(processed_text))
            return matcher.ratio()
        except Exception as e:
            print(f"Error calculating sequence similarity: {e}")
            return 0.0
    
    def calculate_content_coverage(self, original_text: str, processed_text: str) -> float:
        """Calculate how much of the original content is covered in processed text"""
        try:
            original_words = set(self.clean_text(original_text).split())
            processed_words = set(self.clean_text(processed_text).split())
            
            if not original_words:
                return 0.0
            
            # Calculate coverage as intersection over original
            coverage = len(original_words.intersection(processed_words)) / len(original_words)
            return coverage
        except Exception as e:
            print(f"Error calculating content coverage: {e}")
            return 0.0
    
    def extract_key_information(self, processed_data) -> str:
        """Extract key information from processed JSON data"""
        key_info = []
        
        # Handle different JSON structures
        if isinstance(processed_data, list):
            # Unstructured library output format
            for element in processed_data:
                if isinstance(element, dict) and 'text' in element:
                    key_info.append(element['text'])
        elif isinstance(processed_data, dict):
            # Custom metadata format
            # Extract metadata fields
            if 'metadata' in processed_data:
                metadata = processed_data['metadata']
                for field in ['document_title', 'from_whom', 'to_whom', 'job_to_do', 'date', 'deadline']:
                    if field in metadata and metadata[field]:
                        key_info.append(str(metadata[field]))
            
            # Extract extraction text
            if 'extraction_text' in processed_data:
                key_info.append(processed_data['extraction_text'])
            
            # Extract summary if available
            if 'summary' in processed_data:
                if isinstance(processed_data['summary'], dict):
                    for lang_summary in processed_data['summary'].values():
                        key_info.append(str(lang_summary))
                else:
                    key_info.append(str(processed_data['summary']))
        
        return ' '.join(key_info)
    
    def calculate_confidence_score(self, original_pdf_path: str, processed_json_path: str) -> Dict:
        """
        Calculate comprehensive confidence score comparing original PDF with processed JSON
        
        Returns:
        {
            'overall_score': float (0-100),
            'text_similarity': float (0-1),
            'sequence_similarity': float (0-1),
            'content_coverage': float (0-1),
            'details': dict with breakdown
        }
        """
        try:
            # Extract original text from PDF
            original_text = self.extract_pdf_text(original_pdf_path)
            if not original_text:
                return {
                    'overall_score': 0.0,
                    'error': 'Could not extract text from original document'
                }
            
            # Load processed JSON data
            with open(processed_json_path, 'r', encoding='utf-8') as f:
                processed_data = json.load(f)
            
            # Extract processed text
            processed_text = self.extract_key_information(processed_data)
            if not processed_text:
                return {
                    'overall_score': 0.0,
                    'error': 'No processed content found'
                }
            
            # Calculate different similarity metrics
            text_similarity = self.calculate_text_similarity(original_text, processed_text)
            sequence_similarity = self.calculate_sequence_similarity(original_text, processed_text)
            content_coverage = self.calculate_content_coverage(original_text, processed_text)
            
            # Calculate weighted overall score
            # Text similarity: 40%, Sequence similarity: 30%, Content coverage: 30%
            overall_score = (
                text_similarity * 0.4 +
                sequence_similarity * 0.3 +
                content_coverage * 0.3
            ) * 100
            
            # Ensure score is between 0-100
            overall_score = max(0, min(100, overall_score))
            
            return {
                'overall_score': round(overall_score, 1),
                'text_similarity': round(text_similarity, 3),
                'sequence_similarity': round(sequence_similarity, 3),
                'content_coverage': round(content_coverage, 3),
                'details': {
                    'original_length': len(original_text),
                    'processed_length': len(processed_text),
                    'original_words': len(original_text.split()),
                    'processed_words': len(processed_text.split())
                }
            }
            
        except Exception as e:
            return {
                'overall_score': 0.0,
                'error': f'Error calculating confidence: {str(e)}'
            }
    
    def get_confidence_category(self, score: float) -> Tuple[str, str]:
        """Get confidence category and color based on score"""
        if score >= 85:
            return "Excellent", "#4CAF50"
        elif score >= 70:
            return "Good", "#8BC34A"
        elif score >= 55:
            return "Fair", "#FF9800"
        elif score >= 40:
            return "Poor", "#FF5722"
        else:
            return "Very Poor", "#f44336"
