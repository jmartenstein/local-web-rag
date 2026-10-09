import sys
import json
import os
from datetime import datetime
from ddgs import DDGS

def search(query, max_results=5):
    """
    Perform a DuckDuckGo web search and return results.
    
    Args:
        query (str): The search query string
        max_results (int): Maximum number of results to return
    
    Returns:
        list: List of search result dictionaries
    """
    try:
        with DDGS() as ddgs:
            results = []
            for result in ddgs.text(query, max_results=max_results):
                results.append(result)
            return results
    except Exception as e:
        print(f"Error performing search: {e}")
        return []

def save_results_to_file(results, query, output_dir="search_results"):
    """
    Save search results to a JSON file for local storage.
    
    Args:
        results (list): List of search result dictionaries
        query (str): The search query string
        output_dir (str): Directory to save results
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"search_results_{query.replace(' ', '_')}_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    # Prepare data for saving
    data_to_save = {
        "query": query,
        "timestamp": datetime.now().isoformat(),
        "results_count": len(results),
        "results": results
    }
    
    # Save to file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data_to_save, f, indent=2, ensure_ascii=False)
    
    print(f"Results saved to {filepath}")
    return filepath

def format_for_rag(results):
    """
    Format search results for RAG (Retrieval-Augmented Generation) processing.
    
    Args:
        results (list): List of search result dictionaries
    
    Returns:
        str: Formatted text suitable for RAG ingestion
    """
    formatted_text = ""
    for i, result in enumerate(results, 1):
        formatted_text += f"Result {i}:\n"
        formatted_text += f"Title: {result.get('title', 'N/A')}\n"
        formatted_text += f"URL: {result.get('href', 'N/A')}\n"
        formatted_text += f"Body: {result.get('body', 'N/A')}\n"
        formatted_text += "-" * 50 + "\n"
    
    return formatted_text

def main():
    """Main function to run the DuckDuckGo search with local storage capabilities."""
    if len(sys.argv) < 2:
        print("Usage: python duckduckgo_search.py <search_query>")
        print("Example: python duckduckgo_search.py 'python programming'")
        sys.exit(1)
    
    query = " ".join(sys.argv[1:])
    results = search(query)
    
    if results:
        print(f"\nFound {len(results)} results for: '{query}'\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. Title: {result.get('title', 'N/A')}")
            print(f"   URL: {result.get('href', 'N/A')}")
            print(f"   Body: {result.get('body', 'N/A')[:200]}...")
            print()
        
        # Save results locally
        save_results_to_file(results, query)
        
        # Format for RAG processing
        rag_formatted = format_for_rag(results)
        print("RAG-ready formatted text:")
        print("=" * 50)
        print(rag_formatted)
        print("=" * 50)
        
    else:
        print("No results found.")

if __name__ == '__main__':
    main()
