"""
Financial Report Generator

Generates comprehensive markdown financial analysis reports from extracted data.
"""

from typing import Dict, List
from datetime import datetime


class FinancialReportGenerator:
    """Generate comprehensive financial analysis reports."""
    
    def __init__(self):
        """Initialize report generator."""
        pass
    
    def generate_executive_summary(self, company_data: Dict) -> str:
        """Create executive summary with key highlights."""
        ticker = company_data.get('ticker', 'N/A')
        company_name = company_data.get('company_name', 'Unknown')
        year_range = f"{company_data.get('start_year', '')}-{company_data.get('end_year', '')}"
        
        summary = f"""## Executive Summary

**Company**: {company_name} ({ticker})  
**Analysis Period**: {year_range}  
**Reports Analyzed**: {company_data.get('num_reports', 0)}  
**Accounting Standard**: {company_data.get('accounting_standard', 'Unknown')}

### Key Highlights
"""
        
        # Add financial highlights if available
        if 'metrics' in company_data:
            metrics = company_data['metrics']
            if 'profitability' in metrics:
                prof = metrics['profitability']
                if 'ROE' in prof:
                    summary += f"- **Return on Equity**: {prof['ROE']:.2f}%\n"
                if 'net_margin' in prof:
                    summary += f"- **Net Profit Margin**: {prof['net_margin']:.2f}%\n"
        
        return summary
    
    def generate_document_inventory(self, reports: List[Dict]) -> str:
        """Generate document inventory section."""
        inventory = "## Documents Analyzed\n\n"
        inventory += "| Year | Type | Title | Source |\n"
        inventory += "|------|------|-------|--------|\n"
        
        for report in reports:
            year = report.get('year', 'N/A')
            rtype = report.get('type', 'Unknown')
            title = report.get('title', 'Untitled')[:50]
            url = report.get('url', '')
            source = f"[PDF]({url})" if url else "N/A"
            inventory += f"| {year} | {rtype} | {title} | {source} |\n"
        
        return inventory
    
    def generate_metrics_table(self, metrics: Dict) -> str:
        """Generate financial metrics table."""
        table = "## Key Financial Metrics\n\n"
        
        # Profitability Metrics
        if 'profitability' in metrics:
            table += "### Profitability Ratios\n\n"
            table += "| Metric | Value |\n|--------|-------|\n"
            for metric, value in metrics['profitability'].items():
                table += f"| {metric.replace('_', ' ').title()} | {value:.2f}% |\n"
            table += "\n"
        
        # Liquidity Metrics
        if 'liquidity' in metrics:
            table += "### Liquidity Ratios\n\n"
            table += "| Metric | Value |\n|--------|-------|\n"
            for metric, value in metrics['liquidity'].items():
                table += f"| {metric.replace('_', ' ').title()} | {value:.2f} |\n"
            table += "\n"
        
        # Leverage Metrics
        if 'leverage' in metrics:
            table += "### Leverage Ratios\n\n"
            table += "| Metric | Value |\n|--------|-------|\n"
            for metric, value in metrics['leverage'].items():
                table += f"| {metric.replace('_', ' ').title()} | {value:.2f} |\n"
            table += "\n"
        
        return table
    
    def generate_full_report(self, all_data: Dict) -> str:
        """
        Combine all sections into comprehensive markdown report.
        
        Args:
            all_data: Dict containing all analysis data
        
        Returns:
            Complete markdown report
        """
        report_date = datetime.now().strftime("%Y-%m-%d")
        ticker = all_data.get('ticker', 'N/A')
        company_name = all_data.get('company_name', 'Unknown Company')
        
        report = f"""# Financial Analysis Report: {company_name}

**Generated**: {report_date}  
**Ticker**: {ticker}

---

{self.generate_executive_summary(all_data)}

---

{self.generate_document_inventory(all_data.get('reports', []))}

---

{self.generate_metrics_table(all_data.get('metrics', {}))}

---

## Disclaimer

This report is generated automatically from publicly available financial documents.  
All data should be verified against original source documents before making investment decisions.

**Data Sources**: Official company filings and investor relations materials

"""
        
        return report


def main():
    """Test report generator."""
    generator = FinancialReportGenerator()
    
    # Sample data
    sample_data = {
        'ticker': 'AAPL',
        'company_name': 'Apple Inc.',
        'start_year': 2023,
        'end_year': 2024,
        'num_reports': 2,
        'accounting_standard': 'US GAAP',
        'reports': [
            {'year': 2024, 'type': 'Annual', 'title': '2024 Annual Report', 'url': 'https://example.com/report.pdf'},
            {'year': 2023, 'type': 'Annual', 'title': '2023 Annual Report', 'url': 'https://example.com/report2.pdf'}
        ],
        'metrics': {
            'profitability': {'ROE': 25.5, 'net_margin': 21.2},
            'liquidity': {'current_ratio': 1.5, 'quick_ratio': 1.2}
        }
    }
    
    report = generator.generate_full_report(sample_data)
    print(report)


if __name__ == '__main__':
    main()
