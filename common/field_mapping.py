"""
Field mapping functionality for import scripts.

This module provides functions for mapping fields from source data to target fields
in the CSV output, allowing for customization of the CSV structure.
"""

import json
import logging
from typing import Dict, Optional, Any

from common.logging import get_logger

# Default field mappings
DEFAULT_FIELD_MAPPINGS = {
    "title": "title",
    "url": "url",
    "tags": "tags",
    "created": "created",
    "description": "description"
}

def load_field_mappings(field_map_file: Optional[str] = None) -> Dict[str, str]:
    """
    Load field mappings from a JSON file.
    
    Parameters
    ----------
    field_map_file : str, optional
        Path to a JSON file containing field mappings.
        
    Returns
    -------
    Dict[str, str]
        Dictionary mapping source fields to target fields.
    """
    logger = get_logger()
    
    if not field_map_file:
        logger.debug("No field mapping file specified, using default mappings")
        return DEFAULT_FIELD_MAPPINGS.copy()
    
    try:
        with open(field_map_file, 'r') as f:
            mappings = json.load(f)
        
        # Validate the mappings
        if not isinstance(mappings, dict):
            logger.warning(f"Invalid field mappings in {field_map_file}, using default mappings")
            return DEFAULT_FIELD_MAPPINGS.copy()
        
        # Ensure all required fields are present
        for field in DEFAULT_FIELD_MAPPINGS:
            if field not in mappings:
                logger.warning(f"Missing required field '{field}' in mappings, using default")
                mappings[field] = DEFAULT_FIELD_MAPPINGS[field]
        
        logger.info(f"Loaded field mappings from {field_map_file}")
        return mappings
    
    except (IOError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load field mappings from {field_map_file}: {e}")
        logger.info("Using default field mappings")
        return DEFAULT_FIELD_MAPPINGS.copy()

def apply_field_mappings(
    args: Any,
    default_mappings: Optional[Dict[str, str]] = None
) -> Dict[str, str]:
    """
    Apply field mappings from command line arguments.
    
    Parameters
    ----------
    args : Any
        Parsed command line arguments.
    default_mappings : Dict[str, str], optional
        Default field mappings to use as a base.
        
    Returns
    -------
    Dict[str, str]
        Dictionary mapping source fields to target fields.
    """
    logger = get_logger()
    
    # Start with default mappings or load from file
    if default_mappings is None:
        mappings = load_field_mappings(getattr(args, 'field_map', None))
    else:
        mappings = default_mappings.copy()
    
    # Apply individual field mappings from command line arguments
    if hasattr(args, 'map_title') and args.map_title:
        mappings['title'] = args.map_title
        logger.debug(f"Mapping 'title' to '{args.map_title}'")
    
    if hasattr(args, 'map_url') and args.map_url:
        mappings['url'] = args.map_url
        logger.debug(f"Mapping 'url' to '{args.map_url}'")
    
    if hasattr(args, 'map_tags') and args.map_tags:
        mappings['tags'] = args.map_tags
        logger.debug(f"Mapping 'tags' to '{args.map_tags}'")
    
    if hasattr(args, 'map_created') and args.map_created:
        mappings['created'] = args.map_created
        logger.debug(f"Mapping 'created' to '{args.map_created}'")
    
    if hasattr(args, 'map_description') and args.map_description:
        mappings['description'] = args.map_description
        logger.debug(f"Mapping 'description' to '{args.map_description}'")
    
    return mappings

def map_row(row: Dict[str, Any], field_mappings: Dict[str, str]) -> Dict[str, Any]:
    """
    Map a row of data using the provided field mappings.
    
    Parameters
    ----------
    row : Dict[str, Any]
        Row of data with source field names.
    field_mappings : Dict[str, str]
        Dictionary mapping source fields to target fields.
        
    Returns
    -------
    Dict[str, Any]
        Row of data with target field names.
    """
    mapped_row = {}
    
    for source_field, target_field in field_mappings.items():
        if source_field in row:
            mapped_row[target_field] = row[source_field]
    
    # Include any fields that weren't in the mapping
    for field, value in row.items():
        if field not in field_mappings:
            mapped_row[field] = value
    
    return mapped_row

def map_rows(rows: list, field_mappings: Dict[str, str]) -> list:
    """
    Map a list of rows using the provided field mappings.
    
    Parameters
    ----------
    rows : list
        List of rows with source field names.
    field_mappings : Dict[str, str]
        Dictionary mapping source fields to target fields.
        
    Returns
    -------
    list
        List of rows with target field names.
    """
    return [map_row(row, field_mappings) for row in rows]