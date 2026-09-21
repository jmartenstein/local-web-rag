import sys
from duckduckgo_search import DDGS

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

def main():
    """Main function to run the DuckDuckGo search."""
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
    else:
        print("No results found.")

if __name__ == '__main__':
    main()
