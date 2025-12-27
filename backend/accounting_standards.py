"""
Accounting Standards Support

Maps terminology across different accounting standards and provides
country-specific reporting requirement information.
"""

from typing import Dict, List, Optional


class AccountingStandardMapper:
    """Map terminology across different accounting standards."""
    
    # Mapping from US GAAP to IFRS terminology
    GAAP_TO_IFRS = {
        'Inventory': 'Inventories',
        'Property, Plant & Equipment': 'Property, Plant and Equipment',
        'Accounts Receivable': 'Trade Receivables',
        'Accounts Payable': 'Trade Payables',
        'Stockholders Equity': 'Shareholders Equity',
        'Treasury Stock': 'Treasury Shares',
        'Additional Paid-in Capital': 'Share Premium',
        'Accumulated Other Comprehensive Income': 'Reserves',
        'Cost of Goods Sold': 'Cost of Sales',
        'Selling, General & Administrative': 'Administrative Expenses',
        'Research & Development': 'Research and Development',
        'Income Tax Expense': 'Tax Expense',
        'Net Earnings': 'Profit for the Period',
        'Earnings Per Share': 'Earnings Per Share'  # Same term
    }
    
    # Standard-specific keywords for detection
    STANDARD_KEYWORDS = {
        'US GAAP': [
            'generally accepted accounting principles',
            'us gaap',
            'asc',  # Accounting Standards Codification
            'fasb',  # Financial Accounting Standards Board
            'sox'  # Sarbanes-Oxley
        ],
        'IFRS': [
            'international financial reporting standards',
            'ifrs',
            'ias',  # International Accounting Standards
            'iasb',  # International Accounting Standards Board
            'consolidated financial statements ifrs'
        ],
        'Ind AS': [
            'indian accounting standards',
            'ind as',
            'companies act',
            'icai',  # Institute of Chartered Accountants of India
            'mca'  # Ministry of Corporate Affairs
        ],
        'J-GAAP': [
            'japanese gaap',
            'j-gaap',
            'accounting standards board of japan',
            'asbj',
            'financial instruments valuation'
        ],
        'China GAAP': [
            'chinese accounting standards',
            'asbe',  # Accounting Standards for Business Enterprises
            'ministry of finance prc',
            'china accounting standards'
        ]
    }
    
    def normalize_line_item(self, item: str, from_standard: str, to_standard: str = 'IFRS') -> str:
        """
        Normalize line item name across accounting standards.
        
        Args:
            item: Line item name
            from_standard: Source accounting standard
            to_standard: Target accounting standard (default: IFRS)
        
        Returns:
            Normalized line item name
        """
        if from_standard == 'US GAAP' and to_standard == 'IFRS':
            return self.GAAP_TO_IFRS.get(item, item)
        
        # For now, only GAAP to IFRS is implemented
        # Future: Add IFRS to GAAP, Ind AS conversions, etc.
        return item
    
    def detect_standard_from_text(self, text: str) -> str:
        """
        Detect accounting standard from document text.
        
        Args:
            text: Document text (lowercase)
        
        Returns:
            Detected standard: 'US GAAP', 'IFRS', 'Ind AS', 'J-GAAP', 'China GAAP', or 'Unknown'
        """
        text_lower = text.lower()
        
        # Count keyword matches for each standard
        scores = {standard: 0 for standard in self.STANDARD_KEYWORDS}
        
        for standard, keywords in self.STANDARD_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    scores[standard] += 1
        
        # Return standard with highest score
        max_score = max(scores.values())
        if max_score > 0:
            return max(scores, key=scores.get)
        
        return 'Unknown'
    
    def get_standard_requirements(self, standard: str, country: str) -> Dict[str, str]:
        """
        Get reporting requirements for a specific standard/country.
        
        Args:
            standard: Accounting standard
            country: Country name
        
        Returns:
            Dict with reporting requirements
        """
        requirements = {
            'US GAAP': {
                'mandatory_statements': ['Balance Sheet', 'Income Statement', 'Cash Flow Statement', 
                                       'Statement of Stockholders Equity'],
                'filing_frequency': 'Quarterly (10-Q), Annual (10-K)',
                'regulatory_body': 'SEC',
                'audit_required': True,
                'md_and_a_required': True  # Management Discussion & Analysis
            },
            'IFRS': {
                'mandatory_statements': ['Statement of Financial Position', 'Statement of Profit or Loss',
                                       'Statement of Cash Flows', 'Statement of Changes in Equity'],
                'filing_frequency': 'Varies by country (Annual + Interim)',
                'regulatory_body': 'IASB',
                'audit_required': True,
                'md_and_a_required': False
            },
            'Ind AS': {
                'mandatory_statements': ['Balance Sheet', 'Statement of Profit and Loss',
                                       'Cash Flow Statement', 'Statement of Changes in Equity'],
                'filing_frequency': 'Quarterly + Annual',
                'regulatory_body': 'SEBI + MCA',
                'audit_required': True,
                'md_and_a_required': True
            },
            'J-GAAP': {
                'mandatory_statements': ['Balance Sheet', 'Income Statement', 'Cash Flow Statement'],
                'filing_frequency': 'Quarterly + Annual',
                'regulatory_body': 'FSA',
                'audit_required': True,
                'md_and_a_required': False
            }
        }
        
        return requirements.get(standard, {
            'mandatory_statements': ['Unknown'],
            'filing_frequency': 'Unknown',
            'regulatory_body': 'Unknown',
            'audit_required': True,
            'md_and_a_required': False
        })


def main():
    """Test accounting standards mapper."""
    mapper = AccountingStandardMapper()
    
    print("Accounting Standards Mapper")
    print("=" * 60)
    
    # Test line item normalization
    print("\nLine Item Normalization (US GAAP → IFRS):")
    test_items = ['Inventory', 'Accounts Receivable', 'Net Earnings']
    for item in test_items:
        normalized = mapper.normalize_line_item(item, 'US GAAP', 'IFRS')
        print(f"  {item} → {normalized}")
    
    # Test standard detection
    print("\nStandard Detection:")
    text_samples = [
        "prepared in accordance with International Financial Reporting Standards (IFRS)",
        "These financial statements comply with Indian Accounting Standards (Ind AS)",
        "prepared under US GAAP as promulgated by FASB"
    ]
    
    for text in text_samples:
        detected = mapper.detect_standard_from_text(text)
        print(f"  Detected: {detected}")
        print(f"    Text: {text[:60]}...")
    
    # Test requirements
    print("\nUS GAAP Requirements:")
    reqs = mapper.get_standard_requirements('US GAAP', 'United States')
    for key, value in reqs.items():
        print(f"  {key}: {value}")


if __name__ == '__main__':
    main()
