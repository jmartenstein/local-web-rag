#!/usr/bin/env python3
"""
Company Research Script using DuckDuckGo Search Engine

This script performs comprehensive research on companies including:
- Company identification and location verification
- Leadership team investigation
- Company founding date and history
- Funding rounds tracking
- Engineering resume analysis for tech stack detection

Usage:
    python company_research.py <company_name> [--location]
"""

import argparse
import json
import logging
import os
import re
import sys
import traceback
from datetime import datetime
from ddgs import DDGS
from ddgs.exceptions import DDGSException
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import quote

logger = logging.getLogger(__name__)

class SearchError(Exception):
    """Raised when a web search fails (as opposed to returning no results)."""

class CompanyResearcher:
    """Main class for conducting company research using DuckDuckGo."""
    
    def __init__(self, output_dir: str = "search_results", ddgs_factory=DDGS):
        self.output_dir = Path(output_dir)
        self._ddgs_factory = ddgs_factory
        self.results_cache: Dict[str, Any] = {}
        
    def search(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search DuckDuckGo.

        Returns a list of dicts with 'title', 'body' and 'href' keys.
        An empty list means the search worked but found nothing.

        Raises:
            SearchError: if the search itself failed (rate limit, network, etc.).
        """
        try:
            with self._ddgs_factory() as ddgs:
                return list(ddgs.text(query,max_results=max_results))
        except DDGSException as e:
            logger.exception("Search failed for query %r", query)
            raise SearchError(f"Search failed for {query!r}") from e

    def disambiguate_company(self, company_name: str, location: Optional[str] = None) -> Dict:
        """
        Confirm whether there are multiple companies with the same name.
        Returns company info including location if provided.
        """
        search_query = f"{company_name} company"
        if location:
            search_query += f" in {location}"
        
        results = self.search(search_query, max_results=5)
        print(f"[debug] got {len(results)} results; first keys: {list(results[0].keys()) if results else None}")
        
        if not results:
            return {"error": "No companies found", "name": company_name}
        
        # Extract unique companies from results
        companies = []
        for result in results[:5]:
            title = result.get('title', '')
            snippet = result.get('body', '')
            
            # Check if this is a legitimate company (not a person or unrelated entity)
            if 'ompany' in title.lower() or 'inc' in title.lower() or 'llc' in title.lower():
                companies.append({
                    "name": title,
                    "snippet": snippet,
                    "url": result.get('href', '')
                })
        
        # If location was provided, filter by location
        if location:
            location_lower = location.lower()
            filtered_companies = []
            for company in companies:
                combined_text = (company['name'] + ' ' + company['snippet']).lower()
                if location_lower in combined_text:
                    filtered_companies.append(company)
            companies = filtered_companies
        
        return {
            "query": company_name,
            "location": location,
            "companies_found": len(companies),
            "results": companies
        }
    
    def get_leadership_team(self, company_url: str) -> Dict:
        """Investigate leadership team from company website."""
        results = self.search(f"{company_url} leadership team executives", max_results=5)
        
        leaders = []
        for result in results:
            title = result.get('title', '')
            snippet = result.get('body', '')
            
            # Look for CEO, CTO, COO, etc.
            leader_patterns = [
                r'(CEO|Chief Executive Officer)',
                r'(CTO|Chief Technology Officer)',
                r'(COO|Chief Operating Officer)',
                r'(CFO|Chief Financial Officer)',
                r'(Founder)',
                r'(President)'
            ]
            
            for pattern in leader_patterns:
                match = re.search(pattern, title + ' ' + snippet, re.IGNORECASE)
                if match:
                    leaders.append({
                        "role": match.group(1),
                        "name": result.get('title', ''),
                        "snippet": snippet[:200]
                    })
                    break
        
        return {
            "company_url": company_url,
            "leadership": leaders
        }
    
    def get_founding_info(self, company_name: str) -> Dict:
        """Find company founding date and history."""
        results = self.search(f"{company_name} founded year history", max_results=5)
        
        founding_dates = []
        for result in results:
            snippet = result.get('body', '')
            # Look for founding year patterns
            year_matches = re.findall(r'(?:founded|est\.|established)\s*(\d{4})', snippet, re.IGNORECASE)
            if year_matches:
                founding_dates.append({
                    "year": year_matches[0],
                    "source": result.get('title', ''),
                    "snippet": snippet[:150]
                })
        
        return {
            "company_name": company_name,
            "founding_info": founding_dates
        }
    
    def get_funding_rounds(self, company_name: str) -> Dict:
        """Track funding rounds and dates."""
        results = self.search(f"{company_name} funding rounds investment", max_results=10)
        
        rounds = []
        for result in results:
            title = result.get('title', '')
            snippet = result.get('body', '')
            
            # Look for funding round indicators
            funding_patterns = [
                r'(Series\s*\d+)',
                r'(\$\d+\.\d+\s*(?:million|billion))',
                r'(raised)',
                r'(investment)'
            ]
            
            if any(pattern in title.lower() or pattern in snippet.lower() for pattern in funding_patterns):
                rounds.append({
                    "title": title,
                    "snippet": snippet[:200],
                    "url": result.get('href', '')
                })
        
        return {
            "company_name": company_name,
            "funding_rounds": rounds
        }
    
    def get_tech_stack(self, company_url: str) -> Dict:
        """Look for engineering resumes and tech stack information."""
        results = self.search(f"{company_url} engineers careers job postings", max_results=10)
        
        tech_indicators = []
        for result in results:
            snippet = result.get('body', '')
            
            # Look for tech stack indicators
            tech_keywords = [
                'python', 'javascript', 'react', 'node', 'java', 
                'go', 'rust', 'kubernetes', 'docker', 'aws', 'azure',
                'github', 'linkedin', 'engineering', 'developer'
            ]
            
            for keyword in tech_keywords:
                if keyword.lower() in snippet.lower():
                    tech_indicators.append({
                        "tech": keyword,
                        "context": snippet[:100]
                    })
        
        return {
            "company_url": company_url,
            "tech_stack_indicators": tech_indicators
        }
    
    def save_results_to_file(self, results: Dict, query: str, output_dir: str = None) -> str:
        """Save research results to markdown file."""
        if output_dir is None:
            output_dir = self.output_dir
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename from query
        safe_query = re.sub(r'[^\w\s-]', '', query).strip()
        filename = f"{safe_query.replace(' ', '_')}_research.md"
        filepath = output_dir / filename
        
        # Create markdown content
        md_content = f"# Company Research: {query}\n\n"
        md_content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        if 'error' in results:
            md_content += f"**Error**: {results['error']}\n\n"
        else:
            md_content += f"**Query**: {query}\n"
            if 'location' in results:
                md_content += f"**Location Filter**: {results['location']}\n"
            md_content += f"**Companies Found**: {results.get('companies_found', 0)}\n\n"
            
            for i, company in enumerate(results.get('results', []), 1):
                md_content += f"## Company {i}: {company.get('name', 'Unknown')}\n"
                md_content += f"**URL**: {company.get('url', 'N/A')}\n\n"
                md_content += f"{company.get('snippet', '')}\n\n"
            
            # Add leadership info if available
            if 'leadership' in results:
                md_content += "## Leadership Team\n\n"
                for leader in results['leadership']:
                    md_content += f"- **{leader.get('role', 'Unknown')}**: {leader.get('name', 'Unknown')}\n"
            
            # Add founding info if available
            if 'founding_info' in results:
                md_content += "## Founding Information\n\n"
                for info in results['founding_info']:
                    md_content += f"- **Year**: {info.get('year', 'Unknown')}\n"
            
            # Add funding rounds if available
            if 'funding_rounds' in results:
                md_content += "## Funding Rounds\n\n"
                for round in results['funding_rounds']:
                    md_content += f"- **{round.get('title', 'Unknown')}**: {round.get('snippet', '')}\n"
            
            # Add tech stack if available
            if 'tech_stack_indicators' in results:
                md_content += "## Tech Stack Indicators\n\n"
                for tech in results['tech_stack_indicators']:
                    md_content += f"- **{tech.get('tech', 'Unknown')}**: {tech.get('context', '')}\n"
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        return str(filepath)


def main():
    """Main entry point for the company research script."""
    parser = argparse.ArgumentParser(description='Research companies using DuckDuckGo search')
    parser.add_argument('company_name', help='Name of the company to research')
    parser.add_argument('--location', '-l', help='Optional location filter (e.g., "San Francisco")')
    parser.add_argument('--output-dir', '-o', default="search_results", 
                        help='Output directory for markdown files')
    
    args = parser.parse_args()
    
    researcher = CompanyResearcher(output_dir=args.output_dir)
    
    print(f"Starting research for: {args.company_name}")
    if args.location:
        print(f"Location filter: {args.location}")
    
    # Step 1: Disambiguate company name
    print("\n[1/5] Checking for multiple companies with same name...")
    try:
        disambiguation = researcher.disambiguate_company(args.company_name, args.location)
    except SearchError as e:
        print(f"Search failed: {e}")
        sys.exit(2)   
 
    if disambiguation['companies_found'] == 0:
        print("No companies found matching the query.")
        sys.exit(1)
    
    # Use first result as primary company
    primary_company = disambiguation['results'][0]
    company_url = primary_company.get('url', '')
    
    print(f"Primary company identified: {primary_company.get('name', 'Unknown')}")
    
    # Step 2: Get leadership team
    print("\n[2/5] Investigating leadership team...")
    leadership = researcher.get_leadership_team(company_url)
    if leadership['leadership']:
        print(f"Found {len(leadership['leadership'])} leaders")
    else:
        print("No leadership information found")
    
    # Step 3: Get founding info
    print("\n[3/5] Finding founding date and history...")
    founding = researcher.get_founding_info(args.company_name)
    if founding['founding_info']:
        for info in founding['founding_info'][:1]:
            print(f"Founded around: {info.get('year', 'Unknown')}")
    
    # Step 4: Get funding rounds
    print("\n[4/5] Tracking funding rounds...")
    funding = researcher.get_funding_rounds(args.company_name)
    if funding['funding_rounds']:
        print(f"Found {len(funding['funding_rounds'])} funding-related results")
    
    # Step 5: Get tech stack
    print("\n[5/5] Analyzing engineering job postings and tech stack...")
    tech = researcher.get_tech_stack(company_url)
    if tech['tech_stack_indicators']:
        unique_techs = set(t['tech'] for t in tech['tech_stack_indicators'])
        print(f"Potential tech stack: {', '.join(unique_techs)}")
    
    # Save all results
    print("\nSaving results to markdown file...")
    filepath = researcher.save_results_to_file(disambiguation, args.company_name)
    print(f"Results saved to: {filepath}")
    
    print("\nResearch complete!")


if __name__ == '__main__':
    main()
