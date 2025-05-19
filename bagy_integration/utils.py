"""
Utilities for the Bagy to GestãoClick synchronization tool.
"""
import logging
import time
from datetime import datetime

class Pagination:
    """
    Utility class for handling API pagination.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def get_all_pages(self, fetcher, data_key='data', page_param='page', limit_param='limit', limit=100):
        """
        Get all pages from a paginated API using the provided fetcher function.
        
        Args:
            fetcher (callable): Function to fetch a page (fetcher(page=n, limit=m))
            data_key (str): Key in the response that contains the data array
            page_param (str): Parameter name for page in the fetcher
            limit_param (str): Parameter name for limit in the fetcher
            limit (int): Number of items per page
            
        Returns:
            list: All items from all pages
        """
        all_items = []
        page = 1
        keep_fetching = True
        
        while keep_fetching:
            # Build fetcher parameters
            params = {
                page_param: page,
                limit_param: limit
            }
            
            # Fetch current page
            response = fetcher(**params)
            
            # Check if data is available
            if not response or data_key not in response:
                self.logger.warning(f"API response missing '{data_key}' key in page {page}")
                break
            
            # Get items from response
            items = response[data_key]
            
            # Check if we have items
            if not items or len(items) == 0:
                self.logger.info(f"GestãoClick API retornou array vazio em '{data_key}' na página {page}, finalizando paginação")
                break
            
            # Add items to result
            all_items.extend(items)
            
            # Check if we have more pages
            if len(items) < limit:
                # This was the last page
                keep_fetching = False
            else:
                # Continue to next page
                page += 1
        
        self.logger.info(f"Recuperado um total de {len(all_items)} itens de {page} páginas")
        return all_items

def get_current_datetime():
    """
    Get current datetime in ISO format.
    
    Returns:
        str: Current datetime in ISO format
    """
    return datetime.now().isoformat()

def format_duration(seconds):
    """
    Format duration in seconds to a human-readable string.
    
    Args:
        seconds (float): Duration in seconds
        
    Returns:
        str: Formatted duration
    """
    if seconds < 60:
        return f"{seconds:.2f} segundos"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.2f} minutos"
    else:
        hours = seconds / 3600
        return f"{hours:.2f} horas"