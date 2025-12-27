"""
Investor-Report-Finder - CLI Application

Combines LLM-based prompt parsing with web scraping to find investor reports
using natural language queries.

Usage:
    python -m cli.cli "Download the annual report for Apple from 2020"
    python -m cli.cli "Get Microsoft quarterly reports from 2023 to 2024"
"""

import sys
from backend.prompt_parser import PromptParser
from backend.scraper import IRReportFinder


def display_results(reports, parsed_data):
    """Display search results in a user-friendly format.
    
    Args:
        reports: List of report dictionaries from scraper
        parsed_data: Parsed prompt data for context
    """
    print(f"\n{'='*70}")
    print(f"SEARCH RESULTS")
    print(f"{'='*70}")
    print(f"Company: {parsed_data.get('company', 'Unknown')} ({parsed_data.get('ticker', 'N/A')})")
    print(f"Report Type: {parsed_data.get('report_type', 'N/A').title()}")
    print(f"Year Range: {parsed_data.get('start_year', 'N/A')} - {parsed_data.get('end_year', 'N/A')}")
    print(f"{'='*70}\n")
    
    if not reports:
        print("❌ No reports found matching your criteria.\n")
        print("Possible reasons:")
        print("  • Company's IR page blocks scraping (robots.txt)")
        print("  • IR page not found or has non-standard structure")
        print("  • No reports available for the specified year range")
        print("  • Report naming doesn't match expected patterns")
        return
    
    print(f"✅ Found {len(reports)} matching report(s):\n")
    
    for i, report in enumerate(reports, 1):
        print(f"{i}. {report['type'].upper()} REPORT - {report['year']}")
        print(f"   Title: {report['text'][:70]}{'...' if len(report['text']) > 70 else ''}")
        print(f"   URL: {report['url']}")
        print()
    
    print(f"{'='*70}\n")


def main(user_prompt: str):
    """Main application entry point.
    
    Args:
        user_prompt: Natural language query from user
    """
    print(f"\n{'#'*70}")
    print(f"# AI INVESTOR REPORT FINDER")
    print(f"{'#'*70}\n")
    
    # Step 1: Parse the natural language prompt
    print("📝 Step 1: Parsing your query...")
    parser = PromptParser()
    parsed_data = parser.parse_prompt(user_prompt)
    
    # Check if parsing was successful
    if 'error' in parsed_data or not parsed_data.get('ticker'):
        print("\n❌ Failed to parse your query.")
        print("Please provide:")
        print("  • Company name or ticker symbol")
        print("  • Report type (annual or quarterly)")
        print("  • Year or year range")
        print("\nExample: 'Download the annual report for Apple from 2020'\n")
        return
    
    # Step 2: Search for reports
    print(f"\n🔍 Step 2: Searching for {parsed_data['report_type']} reports...")
    finder = IRReportFinder()
    reports = finder.search_from_parsed_prompt(parsed_data)
    
    # Step 3: Display results
    display_results(reports, parsed_data)


def interactive_mode():
    """Interactive mode for continuous queries."""
    print(f"\n{'#'*70}")
    print(f"# AI INVESTOR REPORT FINDER - Interactive Mode")
    print(f"{'#'*70}\n")
    print("Enter your queries in natural language.")
    print("Type 'exit' or 'quit' to stop.\n")
    print("Examples:")
    print("  • Download the annual report for Apple from 2020")
    print("  • Get Microsoft quarterly reports from 2023 to 2024")
    print("  • Find Tesla's 10-K for 2022")
    print()
    
    while True:
        try:
            prompt = input("\n💬 Your query: ").strip()
            
            if prompt.lower() in ['exit', 'quit', 'q']:
                print("\nGoodbye! 👋\n")
                break
            
            if not prompt:
                continue
            
            main(prompt)
            
        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # Command-line mode with query as argument
        query = ' '.join(sys.argv[1:])
        main(query)
    else:
        # Interactive mode
        interactive_mode()
