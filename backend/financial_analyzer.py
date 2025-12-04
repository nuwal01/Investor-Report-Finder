"""
Financial Analyzer

Calculates financial metrics and ratios from extracted financial statement data.
Supports profitability, liquidity, leverage, efficiency ratios and trend analysis.
"""

from typing import Dict, List, Optional
import logging

try:
    import pandas as pd
    import numpy as np
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

logger = logging.getLogger(__name__)


class FinancialAnalyzer:
    """Calculate financial metrics from extracted data."""
    
    def __init__(self):
        """Initialize financial analyzer."""
        if not HAS_PANDAS:
            logger.warning("pandas not available - some calculations may be limited")
    
    def calculate_profitability_ratios(self, financial_data: Dict) -> Dict[str, float]:
        """
        Calculate profitability ratios.
        
        Args:
            financial_data: Dict with keys: net_income, revenue, total_assets, 
                           shareholders_equity, operating_income, gross_profit, etc.
        
        Returns:
            Dict with calculated ratios
        """
        ratios = {}
        
        try:
            # Return on Equity (ROE)
            if financial_data.get('net_income') and financial_data.get('shareholders_equity'):
                ratios['ROE'] = (financial_data['net_income'] / financial_data['shareholders_equity']) * 100
            
            # Return on Assets (ROA)
            if financial_data.get('net_income') and financial_data.get('total_assets'):
                ratios['ROA'] = (financial_data['net_income'] / financial_data['total_assets']) * 100
            
            # Gross Profit Margin
            if financial_data.get('gross_profit') and financial_data.get('revenue'):
                ratios['gross_margin'] = (financial_data['gross_profit'] / financial_data['revenue']) * 100
            
            # Operating Profit Margin
            if financial_data.get('operating_income') and financial_data.get('revenue'):
                ratios['operating_margin'] = (financial_data['operating_income'] / financial_data['revenue']) * 100
            
            # Net Profit Margin
            if financial_data.get('net_income') and financial_data.get('revenue'):
                ratios['net_margin'] = (financial_data['net_income'] / financial_data['revenue']) * 100
            
            # Return on Invested Capital (ROIC)
            if all(k in financial_data for k in ['nopat', 'invested_capital']):
                ratios['ROIC'] = (financial_data['nopat'] / financial_data['invested_capital']) * 100
        
        except Exception as e:
            logger.error(f"Error calculating profitability ratios: {e}")
        
        return ratios
    
    def calculate_liquidity_ratios(self, balance_sheet: Dict) -> Dict[str, float]:
        """
        Calculate liquidity ratios.
        
        Args:
            balance_sheet: Dict with current_assets, current_liabilities, cash, etc.
        
        Returns:
            Dict with calculated ratios
        """
        ratios = {}
        
        try:
            # Current Ratio
            if balance_sheet.get('current_assets') and balance_sheet.get('current_liabilities'):
                ratios['current_ratio'] = balance_sheet['current_assets'] / balance_sheet['current_liabilities']
            
            # Quick Ratio (Acid Test)
            if all(k in balance_sheet for k in ['current_assets', 'inventory', 'current_liabilities']):
                quick_assets = balance_sheet['current_assets'] - balance_sheet['inventory']
                ratios['quick_ratio'] = quick_assets / balance_sheet['current_liabilities']
            
            # Cash Ratio
            if balance_sheet.get('cash_and_equivalents') and balance_sheet.get('current_liabilities'):
                ratios['cash_ratio'] = balance_sheet['cash_and_equivalents'] / balance_sheet['current_liabilities']
        
        except Exception as e:
            logger.error(f"Error calculating liquidity ratios: {e}")
        
        return ratios
    
    def calculate_leverage_ratios(self, financial_data: Dict) -> Dict[str, float]:
        """
        Calculate leverage/solvency ratios.
        
        Args:
            financial_data: Dict with total_debt, total_equity, ebit, interest_expense, etc.
        
        Returns:
            Dict with calculated ratios
        """
        ratios = {}
        
        try:
            # Debt-to-Equity Ratio
            if financial_data.get('total_debt') and financial_data.get('total_equity'):
                ratios['debt_to_equity'] = financial_data['total_debt'] / financial_data['total_equity']
            
            # Interest Coverage Ratio
            if financial_data.get('ebit') and financial_data.get('interest_expense'):
                if financial_data['interest_expense'] != 0:
                    ratios['interest_coverage'] = financial_data['ebit'] / financial_data['interest_expense']
            
            # Debt-to-EBITDA
            if financial_data.get('total_debt') and financial_data.get('ebitda'):
                ratios['debt_to_ebitda'] = financial_data['total_debt'] / financial_data['ebitda']
            
            # Debt Ratio
            if financial_data.get('total_debt') and financial_data.get('total_assets'):
                ratios['debt_ratio'] = financial_data['total_debt'] / financial_data['total_assets']
        
        except Exception as e:
            logger.error(f"Error calculating leverage ratios: {e}")
        
        return ratios
    
    def calculate_efficiency_ratios(self, financial_data: Dict) -> Dict[str, float]:
        """
        Calculate efficiency/activity ratios.
        
        Args:
            financial_data: Dict with revenue, assets, inventory, receivables, etc.
        
        Returns:
            Dict with calculated ratios
        """
        ratios = {}
        
        try:
            # Asset Turnover
            if financial_data.get('revenue') and financial_data.get('total_assets'):
                ratios['asset_turnover'] = financial_data['revenue'] / financial_data['total_assets']
            
            # Inventory Turnover
            if financial_data.get('cogs') and financial_data.get('average_inventory'):
                ratios['inventory_turnover'] = financial_data['cogs'] / financial_data['average_inventory']
            
            # Receivables Turnover
            if financial_data.get('revenue') and financial_data.get('average_receivables'):
                ratios['receivables_turnover'] = financial_data['revenue'] / financial_data['average_receivables']
            
            # Days Sales Outstanding (DSO)
            if 'receivables_turnover' in ratios and ratios['receivables_turnover'] != 0:
                ratios['days_sales_outstanding'] = 365 / ratios['receivables_turnover']
        
        except Exception as e:
            logger.error(f"Error calculating efficiency ratios: {e}")
        
        return ratios
    
    def calculate_all_metrics(self, financial_data: Dict) -> Dict[str, Dict[str, float]]:
        """
        Calculate all financial metrics.
        
        Args:
            financial_data: Comprehensive financial data dict
        
        Returns:
            Dict organized by metric category
        """
        return {
            'profitability': self.calculate_profitability_ratios(financial_data),
            'liquidity': self.calculate_liquidity_ratios(financial_data),
            'leverage': self.calculate_leverage_ratios(financial_data),
            'efficiency': self.calculate_efficiency_ratios(financial_data)
        }
    
    def perform_trend_analysis(self, multi_year_data: List[Dict]) -> Dict:
        """
        Analyze year-over-year and quarter-over-quarter trends.
        
        Args:
            multi_year_data: List of financial_data dicts for different periods
        
        Returns:
            Dict with trend analysis
        """
        if not HAS_PANDAS:
            logger.error("pandas required for trend analysis")
            return {}
        
        trends = {}
        
        try:
            # Convert to DataFrame for easier analysis
            df = pd.DataFrame(multi_year_data)
            
            # Year-over-Year growth rates
            if 'revenue' in df.columns:
                trends['revenue_yoy_growth'] = df['revenue'].pct_change() * 100
            
            if 'net_income' in df.columns:
                trends['net_income_yoy_growth'] = df['net_income'].pct_change() * 100
            
            # Compound Annual Growth Rate (CAGR)
            if len(df) > 1 and 'revenue' in df.columns:
                years = len(df) - 1
                cagr = (((df['revenue'].iloc[-1] / df['revenue'].iloc[0]) ** (1/years)) - 1) * 100
                trends['revenue_cagr'] = cagr
        
        except Exception as e:
            logger.error(f"Error performing trend analysis: {e}")
        
        return trends


def main():
    """Test the financial analyzer."""
    analyzer = FinancialAnalyzer()
    
    # Example data
    sample_data = {
        'net_income': 100000000,
        'revenue': 500000000,
        'total_assets': 1000000000,
        'shareholders_equity': 400000000,
        'operating_income': 150000000,
        'gross_profit': 250000000
    }
    
    print("Financial Analyzer initialized")
    print(f"pandas available: {HAS_PANDAS}")
    print("\nSample profitability ratios:")
    ratios = analyzer.calculate_profitability_ratios(sample_data)
    for metric, value in ratios.items():
        print(f"  {metric}: {value:.2f}%")


if __name__ == '__main__':
    main()
