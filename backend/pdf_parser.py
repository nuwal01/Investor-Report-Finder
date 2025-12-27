"""
PDF Financial Data Parser

Extracts financial statements and data from PDF investor reports.
Supports multiple approaches: table detection, LLM-based extraction, and pattern matching.
"""

import os
import re
from typing import Dict, List, Optional, Tuple
import logging

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

logger = logging.getLogger(__name__)


class FinancialPDFParser:
    """Extract financial statements from PDF reports."""
    
    def __init__(self, use_llm: bool = False):
        """
        Initialize PDF parser.
        
        Args:
            use_llm: Use LLM for extraction (requires OpenAI API key)
        """
        if not HAS_PDFPLUMBER:
            raise ImportError("pdfplumber is required. Install with: pip install pdfplumber")
        
        self.use_llm = use_llm
        if use_llm:
            try:
                from openai import OpenAI
                self.llm_client = OpenAI()
            except ImportError:
                logger.warning("OpenAI not available, falling back to rule-based extraction")
                self.use_llm = False
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract all text from PDF file."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""
                return text
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
            return ""
    
    def extract_tables_from_pdf(self, pdf_path: str) -> List[pd.DataFrame]:
        """Extract all tables from PDF file."""
        if not HAS_PANDAS:
            logger.error("pandas is required for table extraction")
            return []
        
        tables = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()
                    for table in page_tables:
                        if table and len(table) > 1:  # At least header + 1 row
                            df = pd.DataFrame(table[1:], columns=table[0])
                            df['source_page'] = page_num + 1
                            tables.append(df)
        except Exception as e:
            logger.error(f"Error extracting tables from {pdf_path}: {e}")
        
        return tables
    
    def find_financial_statement_tables(self, tables: List[pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Identify which tables contain financial statements.
        
        Returns:
            Dictionary with keys: 'income_statement', 'balance_sheet', 'cash_flow'
        """
        statements = {}
        
        for table in tables:
            table_str = str(table.columns) + str(table.head())
            table_lower = table_str.lower()
            
            # Income Statement indicators
            if any(keyword in table_lower for keyword in ['revenue', 'net income', 'operating income', 'earnings']):
                if 'income_statement' not in statements:
                    statements['income_statement'] = table
            
            # Balance Sheet indicators
            elif any(keyword in table_lower for keyword in ['total assets', 'total liabilities', 'shareholders equity']):
                if 'balance_sheet' not in statements:
                    statements['balance_sheet'] = table
            
            # Cash Flow indicators
            elif any(keyword in table_lower for keyword in ['cash flow', 'operating activities', 'investing activities']):
                if 'cash_flow' not in statements:
                    statements['cash_flow'] = table
        
        return statements
    
    def extract_income_statement(self, pdf_path: str) -> Optional[pd.DataFrame]:
        """Extract income statement from PDF."""
        tables = self.extract_tables_from_pdf(pdf_path)
        statements = self.find_financial_statement_tables(tables)
        return statements.get('income_statement')
    
    def extract_balance_sheet(self, pdf_path: str) -> Optional[pd.DataFrame]:
        """Extract balance sheet from PDF."""
        tables = self.extract_tables_from_pdf(pdf_path)
        statements = self.find_financial_statement_tables(tables)
        return statements.get('balance_sheet')
    
    def extract_cash_flow(self, pdf_path: str) -> Optional[pd.DataFrame]:
        """Extract cash flow statement from PDF."""
        tables = self.extract_tables_from_pdf(pdf_path)
        statements = self.find_financial_statement_tables(tables)
        return statements.get('cash_flow')
    
    def detect_accounting_standard(self, pdf_path: str) -> str:
        """
        Detect accounting standard used in the document.
        
        Returns:
            One of: 'US GAAP', 'IFRS', 'Ind AS', 'J-GAAP', 'Unknown'
        """
        text = self.extract_text_from_pdf(pdf_path)
        text_lower = text.lower()
        
        # Check for standard indicators
        if 'generally accepted accounting principles' in text_lower or 'us gaap' in text_lower:
            return 'US GAAP'
        elif 'international financial reporting standards' in text_lower or 'ifrs' in text_lower:
            return 'IFRS'
        elif 'indian accounting standards' in text_lower or 'ind as' in text_lower:
            return 'Ind AS'
        elif 'japanese gaap' in text_lower or 'j-gaap' in text_lower:
            return 'J-GAAP'
        else:
            return 'Unknown'
    
    def extract_all_statements(self, pdf_path: str) -> Dict[str, any]:
        """
        Extract all financial data from PDF.
        
        Returns:
            Dictionary containing all extracted financial data
        """
        return {
            'income_statement': self.extract_income_statement(pdf_path),
            'balance_sheet': self.extract_balance_sheet(pdf_path),
            'cash_flow': self.extract_cash_flow(pdf_path),
            'accounting_standard': self.detect_accounting_standard(pdf_path),
            'full_text': self.extract_text_from_pdf(pdf_path)
        }


def main():
    """Test the PDF parser."""
    parser = FinancialPDFParser(use_llm=False)
    
    # Test with a sample PDF (user should provide path)
    print("PDF Financial Parser initialized")
    print(f"pdfplumber available: {HAS_PDFPLUMBER}")
    print(f"pandas available: {HAS_PANDAS}")
    print("\nTo use: parser.extract_all_statements('path/to/report.pdf')")


if __name__ == '__main__':
    main()
