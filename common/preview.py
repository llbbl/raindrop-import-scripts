"""
Preview functionality for import scripts.

This module provides functions for previewing data before importing it.
"""

import logging
import textwrap
from typing import Dict, List, Any, Optional

from common.logging import get_logger

def preview_items(
    items: List[Dict[str, Any]],
    limit: int = 10,
    title_field: str = "title",
    url_field: str = "url",
    tags_field: str = "tags",
    created_field: str = "created",
    description_field: Optional[str] = "description"
) -> None:
    """
    Preview a list of items that will be imported.
    
    Parameters
    ----------
    items : List[Dict[str, Any]]
        List of items to preview.
    limit : int, optional
        Maximum number of items to preview (default: 10).
    title_field : str, optional
        Field name for the title (default: "title").
    url_field : str, optional
        Field name for the URL (default: "url").
    tags_field : str, optional
        Field name for the tags (default: "tags").
    created_field : str, optional
        Field name for the created date (default: "created").
    description_field : str, optional
        Field name for the description (default: "description").
        
    Returns
    -------
    None
        The function prints the preview to the console.
    """
    logger = get_logger()
    
    if not items:
        logger.info("No items to preview")
        return
    
    total_items = len(items)
    preview_count = min(limit, total_items)
    
    logger.info(f"Previewing {preview_count} of {total_items} items:")
    
    for i, item in enumerate(items[:preview_count], 1):
        logger.info(f"\n--- Item {i} of {preview_count} ---")
        
        # Title
        title = item.get(title_field, "No title")
        logger.info(f"Title: {title}")
        
        # URL
        url = item.get(url_field, "No URL")
        logger.info(f"URL: {url}")
        
        # Tags
        tags = item.get(tags_field, "")
        if tags:
            logger.info(f"Tags: {tags}")
        
        # Created date
        created = item.get(created_field, "")
        if created:
            logger.info(f"Created: {created}")
        
        # Description (truncated if too long)
        if description_field and description_field in item:
            description = item[description_field]
            if description:
                # Truncate and wrap long descriptions
                if len(description) > 200:
                    description = description[:197] + "..."
                
                # Wrap text for better readability
                wrapped_description = textwrap.fill(description, width=80)
                logger.info(f"Description: {wrapped_description}")
    
    if total_items > preview_count:
        logger.info(f"\n... and {total_items - preview_count} more items (use --preview-limit to show more)")