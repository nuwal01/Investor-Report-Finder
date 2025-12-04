"""
International Ticker Parser

Parses ticker symbols from global markets and provides country/exchange metadata.
Supports major exchanges worldwide including US, India, Japan, UK, Hong Kong, etc.
"""

from typing import Dict, Optional
import re


class TickerParser:
    """Parse international ticker symbols and determine exchange/country."""
    
    # Exchange suffix to country/exchange/currency mapping
    EXCHANGE_MAPPING = {
        # Indian Exchanges
        'NS': {
            'country': 'India',
            'exchange': 'NSE',
            'exchange_full': 'National Stock Exchange of India',
            'currency': 'INR',
            'regulatory_body': 'SEBI',
            'accounting_standard': 'Ind AS',
            'report_name': 'Annual Report',
            'quarterly_name': 'Quarterly Report'
        },
        'BO': {
            'country': 'India',
            'exchange': 'BSE',
            'exchange_full': 'Bombay Stock Exchange',
            'currency': 'INR',
            'regulatory_body': 'SEBI',
            'accounting_standard': 'Ind AS',
            'report_name': 'Annual Report',
            'quarterly_name': 'Quarterly Report'
        },
        
        # Japanese Exchanges
        'T': {
            'country': 'Japan',
            'exchange': 'TSE',
            'exchange_full': 'Tokyo Stock Exchange',
            'currency': 'JPY',
            'regulatory_body': 'FSA',
            'accounting_standard': 'J-GAAP',
            'report_name': '有価証券報告書',  # Securities Report
            'quarterly_name': '四半期報告書'  # Quarterly Securities Report
        },
        'JP': {
            'country': 'Japan',
            'exchange': 'TSE',
            'exchange_full': 'Tokyo Stock Exchange',
            'currency': 'JPY',
            'regulatory_body': 'FSA',
            'accounting_standard': 'J-GAAP',
            'report_name': '有価証券報告書',
            'quarterly_name': '四半期報告書'
        },
        
        # UK Exchanges
        'L': {
            'country': 'United Kingdom',
            'exchange': 'LSE',
            'exchange_full': 'London Stock Exchange',
            'currency': 'GBP',
            'regulatory_body': 'FCA',
            'accounting_standard': 'IFRS',
            'report_name': 'Annual Report',
            'quarterly_name': 'Interim Report'
        },
        
        # Hong Kong
        'HK': {
            'country': 'Hong Kong',
            'exchange': 'HKEX',
            'exchange_full': 'Hong Kong Stock Exchange',
            'currency': 'HKD',
            'regulatory_body': 'SFC',
            'accounting_standard': 'HKFRS',
            'report_name': 'Annual Report',
            'quarterly_name': 'Interim Report'
        },
        
        # Australian Exchanges
        'AX': {
            'country': 'Australia',
            'exchange': 'ASX',
            'exchange_full': 'Australian Securities Exchange',
            'currency': 'AUD',
            'regulatory_body': 'ASIC',
            'accounting_standard': 'AASB',
            'report_name': 'Annual Report',
            'quarterly_name': 'Quarterly Report'
        },
        
        # Canadian Exchanges
        'TO': {
            'country': 'Canada',
            'exchange': 'TSX',
            'exchange_full': 'Toronto Stock Exchange',
            'currency': 'CAD',
            'regulatory_body': 'IIROC',
            'accounting_standard': 'IFRS',
            'report_name': 'Annual Report',
            'quarterly_name': 'Quarterly Report'
        },
        
        # Chinese Exchanges
        'SS': {
            'country': 'China',
            'exchange': 'SSE',
            'exchange_full': 'Shanghai Stock Exchange',
            'currency': 'CNY',
            'regulatory_body': 'CSRC',
            'accounting_standard': 'China GAAP',
            'report_name': '年度报告',  # Annual Report
            'quarterly_name': '季度报告'  # Quarterly Report
        },
        'SZ': {
            'country': 'China',
            'exchange': 'SZSE',
            'exchange_full': 'Shenzhen Stock Exchange',
            'currency': 'CNY',
            'regulatory_body': 'CSRC',
            'accounting_standard': 'China GAAP',
            'report_name': '年度报告',
            'quarterly_name': '季度报告'
        },
        
        # Singapore
        'SI': {
            'country': 'Singapore',
            'exchange': 'SGX',
            'exchange_full': 'Singapore Exchange',
            'currency': 'SGD',
            'regulatory_body': 'MAS',
            'accounting_standard': 'SFRS',
            'report_name': 'Annual Report',
            'quarterly_name': 'Quarterly Report'
        },
        
        # South Korea
        'KS': {
            'country': 'South Korea',
            'exchange': 'KRX',
            'exchange_full': 'Korea Exchange',
            'currency': 'KRW',
            'regulatory_body': 'FSC',
            'accounting_standard': 'K-IFRS',
            'report_name': '사업보고서',  # Business Report
            'quarterly_name': '분기보고서'  # Quarterly Report
        },
        
        # Germany
        'DE': {
            'country': 'Germany',
            'exchange': 'XETRA',
            'exchange_full': 'Deutsche Börse',
            'currency': 'EUR',
            'regulatory_body': 'BaFin',
            'accounting_standard': 'IFRS',
            'report_name': 'Geschäftsbericht',  # Annual Report
            'quarterly_name': 'Quartalsbericht'  # Quarterly Report
        },
        
        # France
        'PA': {
            'country': 'France',
            'exchange': 'Euronext Paris',
            'exchange_full': 'Euronext Paris',
            'currency': 'EUR',
            'regulatory_body': 'AMF',
            'accounting_standard': 'IFRS',
            'report_name': 'Rapport Annuel',  # Annual Report
            'quarterly_name': 'Rapport Trimestriel'  # Quarterly Report
        },
        
        # Switzerland
        'SW': {
            'country': 'Switzerland',
            'exchange': 'SIX',
            'exchange_full': 'SIX Swiss Exchange',
            'currency': 'CHF',
            'regulatory_body': 'FINMA',
            'accounting_standard': 'IFRS',
            'report_name': 'Annual Report',
            'quarterly_name': 'Interim Report'
        },
        
        # Brazil
        'SA': {
            'country': 'Brazil',
            'exchange': 'B3',
            'exchange_full': 'B3 - Brasil Bolsa Balcão',
            'currency': 'BRL',
            'regulatory_body': 'CVM',
            'accounting_standard': 'BR GAAP',
            'report_name': 'Relatório Anual',  # Annual Report
            'quarterly_name': 'ITR'  # Quarterly Information
        }
    }
    
    # US exchanges (no suffix or specific suffixes)
    US_SUFFIXES = ['', None]  # No suffix typically means US
    US_INFO = {
        'country': 'United States',
        'exchange': 'NYSE/NASDAQ',
        'exchange_full': 'New York Stock Exchange / NASDAQ',
        'currency': 'USD',
        'regulatory_body': 'SEC',
        'accounting_standard': 'US GAAP',
        'report_name': '10-K',
        'quarterly_name': '10-Q'
    }
    
    def parse_ticker(self, ticker: str) -> Dict[str, str]:
        """
        Parse ticker symbol and extract country/exchange information.
        
        Args:
            ticker: Ticker symbol (e.g., 'AAPL', 'RELIANCE.NS', '7203.T')
            
        Returns:
            Dictionary with country, exchange, currency, etc.
        """
        if not ticker:
            raise ValueError("Ticker symbol cannot be empty")
        
        ticker = ticker.strip().upper()
        
        # Check if ticker has a suffix
        if '.' in ticker:
            base_ticker, suffix = ticker.rsplit('.', 1)
            
            if suffix in self.EXCHANGE_MAPPING:
                info = self.EXCHANGE_MAPPING[suffix].copy()
                info['ticker'] = ticker
                info['base_ticker'] = base_ticker
                info['suffix'] = suffix
                return info
            else:
                # Unknown suffix, treat as US
                return self._get_us_ticker_info(ticker)
        else:
            # No suffix, treat as US
            return self._get_us_ticker_info(ticker)
    
    def _get_us_ticker_info(self, ticker: str) -> Dict[str, str]:
        """Get info for US ticker."""
        info = self.US_INFO.copy()
        info['ticker'] = ticker
        info['base_ticker'] = ticker
        info['suffix'] = None
        return info
    
    def get_search_keywords(self, ticker_info: Dict[str, str], report_type: str) -> Dict[str, str]:
        """
        Get country-specific search keywords for report types.
        
        Args:
            ticker_info: Output from parse_ticker()
            report_type: 'annual', 'quarterly', 'earnings', etc.
            
        Returns:
            Dictionary with search keywords for that country/report type
        """
        country = ticker_info['country']
        
        keywords = {
            'annual': ticker_info.get('report_name', 'Annual Report'),
            'quarterly': ticker_info.get('quarterly_name', 'Quarterly Report'),
            'earnings': 'Earnings Release',
            'presentation': 'Investor Presentation',
            '8-k': 'Current Report' if country == 'United States' else 'Material Event Disclosure',
            'financial_statements': 'Financial Statements'
        }
        
        return {
            'primary': keywords.get(report_type, 'Annual Report'),
            'exchange': ticker_info['exchange'],
            'country': country
        }
    
    def build_search_query(
        self,
        ticker: str,
        year: int,
        report_type: str = 'annual'
    ) -> str:
        """
        Build country-specific search query.
        
        Args:
            ticker: Full ticker (e.g., 'RELIANCE.NS')
            year: Year to search for
            report_type: Type of report
            
        Returns:
            Optimized search query string
        """
        ticker_info = self.parse_ticker(ticker)
        keywords = self.get_search_keywords(ticker_info, report_type)
        
        base_ticker = ticker_info['base_ticker']
        exchange = ticker_info['exchange']
        
        # Build query based on country
        if ticker_info['country'] == 'United States':
            # US-specific query
            if report_type == 'annual':
                query = f'{base_ticker} {year} "10-K" annual report filetype:pdf -10-Q'
            elif report_type == 'quarterly':
                query = f'{base_ticker} {year} "10-Q" quarterly report filetype:pdf -10-K site:sec.gov'
            else:
                query = f'{base_ticker} {year} {keywords["primary"]} filetype:pdf'
        
        elif ticker_info['country'] == 'India':
            # Indian companies
            query = f'{base_ticker} {year} "{keywords["primary"]}" {exchange} BSE NSE filetype:pdf'
        
        elif ticker_info['country'] == 'Japan':
            # Japanese companies (mix English and Japanese)
            if report_type == 'annual':
                query = f'{base_ticker} {year} 有価証券報告書 annual report filetype:pdf'
            else:
                query = f'{base_ticker} {year} {keywords["primary"]} filetype:pdf'
        
        else:
            # Generic international query
            query = f'{base_ticker} {year} "{keywords["primary"]}" {exchange} filetype:pdf'
        
        return query
    
    def get_regulatory_filing_url(self, ticker_info: Dict[str, str]) -> Optional[str]:
        """
        Get regulatory filing website base URL for the exchange.
        
        Args:
            ticker_info: Output from parse_ticker()
            
        Returns:
            Base URL for regulatory filings or None
        """
        regulatory_urls = {
            'SEC': 'https://www.sec.gov/edgar/searchedgar/companysearch.html',
            'SEBI': 'https://www.bseindia.com',
            'FSA': 'https://disclosure.edinet-fsa.go.jp',
            'FCA': 'https://www.fca.org.uk',
            'SFC': 'https://www.hkexnews.hk',
            'ASIC': 'https://www.asx.com.au',
            'CSRC': 'http://www.csrc.gov.cn'
        }
        
        regulatory_body = ticker_info.get('regulatory_body')
        return regulatory_urls.get(regulatory_body)


def main():
    """Test the ticker parser."""
    parser = TickerParser()
    
    test_tickers = [
        'AAPL',           # US
        'RELIANCE.NS',    # India NSE
        '7203.T',         # Japan (Toyota)
        'VOD.L',          # UK (Vodafone)
        '0700.HK',        # Hong Kong (Tencent)
        'BHP.AX',         # Australia
        'SHOP.TO',        # Canada
        '600519.SS',      # China Shanghai
    ]
    
    print("Testing Ticker Parser\n" + "="*60)
    
    for ticker in test_tickers:
        print(f"\nTicker: {ticker}")
        info = parser.parse_ticker(ticker)
        print(f"  Country: {info['country']}")
        print(f"  Exchange: {info['exchange_full']}")
        print(f"  Currency: {info['currency']}")
        print(f"  Accounting: {info['accounting_standard']}")
        
        query = parser.build_search_query(ticker, 2023, 'annual')
        print(f"  Search Query: {query}")


if __name__ == '__main__':
    main()
