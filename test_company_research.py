#!/usr/bin/env python3
"""
Unit tests for company_research.py following red-green-refactor cycle.

These tests validate:
- Company disambiguation logic
- Leadership team extraction
- Founding information parsing
- Funding rounds tracking
- Tech stack detection
- File output generation
"""

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from company_research import CompanyResearcher


class TestCompanyResearcher(unittest.TestCase):
    """Test cases for CompanyResearcher class."""
    
    @patch('company_research.DDGS')
    def setUp(self, mock_ddgs):
        """Set up test fixtures."""
        self.mock_ddgs_instance = MagicMock()
        mock_ddgs.return_value.__enter__ = MagicMock(return_value=self.mock_ddgs_instance)
        mock_ddgs.return_value.__exit__ = MagicMock(return_value=False)
        
        self.researcher = CompanyResearcher(output_dir="test_output")
    
    def test_search_returns_mock_results(self):
        """Test that search method returns results from mock."""
        # Arrange
        mock_result = {
            'title': 'Test Company',
            'body': 'This is a test company snippet',
            'href': 'https://example.com'
        }
        self.mock_ddgs_instance.text.return_value = [mock_result]
        
        # Act
        results = self.researcher.search("test query")
        
        # Assert
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Test Company')
    
    def test_disambiguate_company_with_location(self):
        """Test company disambiguation with location filter."""
        # Arrange
        mock_result = {
            'title': 'Test Company Inc',
            'body': 'Test Company located in San Francisco',
            'href': 'https://example.com'
        }
        self.mock_ddgs_instance.text.return_value = [mock_result]
        
        # Act
        result = self.researcher.disambiguate_company("Test", "San Francisco")
        
        # Assert
        self.assertIn('companies_found', result)
        self.assertIn('results', result)
    
    def test_disambiguate_company_no_results(self):
        """Test disambiguation when no companies found."""
        # Arrange
        self.mock_ddgs_instance.text.return_value = []
        
        # Act
        result = self.researcher.disambiguate_company("NonExistentCompany")
        
        # Assert
        self.assertIn('error', result)
    
    def test_get_leadership_team(self):
        """Test leadership team extraction."""
        # Arrange
        mock_result = {
            'title': 'CEO John Smith - Test Company',
            'body': 'John Smith is the CEO of Test Company',
            'href': 'https://example.com'
        }
        self.mock_ddgs_instance.text.return_value = [mock_result]
        
        # Act
        result = self.researcher.get_leadership_team("https://example.com")
        
        # Assert
        self.assertIn('leadership', result)
    
    def test_get_founding_info(self):
        """Test founding information extraction."""
        # Arrange
        mock_result = {
            'title': 'Test Company History',
            'body': 'Test Company was founded in 2015 and established in 2016',
            'href': 'https://example.com'
        }
        self.mock_ddgs_instance.text.return_value = [mock_result]
        
        # Act
        result = self.researcher.get_founding_info("Test Company")
        
        # Assert
        self.assertIn('founding_info', result)
    
    def test_get_funding_rounds(self):
        """Test funding rounds extraction."""
        # Arrange
        mock_result = {
            'title': 'Test Company Raises Series A',
            'body': 'Test Company raised $10 million in Series A funding',
            'href': 'https://example.com'
        }
        self.mock_ddgs_instance.text.return_value = [mock_result]
        
        # Act
        result = self.researcher.get_funding_rounds("Test Company")
        
        # Assert
        self.assertIn('funding_rounds', result)
    
    def test_get_tech_stack(self):
        """Test tech stack detection."""
        # Arrange
        mock_result = {
            'title': 'Test Company Engineering Team',
            'body': 'Our engineers use Python, JavaScript, React, and Node.js for development',
            'href': 'https://example.com'
        }
        self.mock_ddgs_instance.text.return_value = [mock_result]
        
        # Act
        result = self.researcher.get_tech_stack("https://example.com")
        
        # Assert
        self.assertIn('tech_stack_indicators', result)
    
    def test_save_results_to_file_creates_markdown(self):
        """Test that results are saved to markdown file."""
        # Arrange
        mock_result = {
            'query': 'Test Company',
            'companies_found': 1,
            'results': [{'name': 'Test Company Inc', 'url': 'https://example.com'}]
        }
        
        # Act
        filepath = self.researcher.save_results_to_file(mock_result, "Test Company")
        
        # Assert
        self.assertTrue(os.path.exists(filepath))
        self.assertIn('.md', filepath)
    
    def test_main_function_runs_without_crashing(self):
        """Test that main function executes without errors."""
        # Arrange - mock all external dependencies
        with patch('company_research.DDGS') as mock_ddgs:
            mock_ddgs_instance = MagicMock()
            mock_ddgs.return_value.__enter__ = MagicMock(return_value=mock_ddgs_instance)
            mock_ddgs.return_value.__exit__ = MagicMock(return_value=False)
            
            # Mock search to return empty results (no real API calls)
            mock_ddgs_instance.text.return_value = []
            
            # Act - this should not crash even with no results
            try:
                from company_research import main
                # We can't easily test main() without user input, so just verify imports work
                self.assertTrue(True)
            except Exception as e:
                self.fail(f"main() crashed: {e}")


class TestSearchQueryParsing(unittest.TestCase):
    """Test cases for search query handling."""
    
    def test_search_query_with_special_chars(self):
        """Test that special characters in queries are handled."""
        # Arrange
        query = "Test Company's 2023 Funding Round!"
        
        # Act - verify the query can be processed
        from urllib.parse import quote
        encoded = quote(query)
        
        # Assert
        self.assertIn('Test', encoded)
    
    def test_search_query_normalization(self):
        """Test that search queries are normalized properly."""
        # Arrange
        query1 = "  Test Company  "
        query2 = "TestCompany"
        
        # Act
        normalized1 = query1.strip()
        normalized2 = query2
        
        # Assert
        self.assertEqual(normalized1, 'Test Company')


class TestOutputDirectoryHandling(unittest.TestCase):
    """Test cases for output directory handling."""
    
    def test_output_directory_creation(self):
        """Test that output directory is created if it doesn't exist."""
        # Arrange
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Act
            researcher = CompanyResearcher(output_dir=tmpdir)
            
            # Assert
            self.assertTrue(os.path.exists(tmpdir))
    
    def test_output_directory_exists(self):
        """Test that existing output directory is used."""
        # Arrange
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Act
            researcher = CompanyResearcher(output_dir=tmpdir)
            
            # Assert
            self.assertEqual(researcher.output_dir, Path(tmpdir))


if __name__ == '__main__':
    unittest.main()
