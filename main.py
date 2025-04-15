#!/usr/bin/env python3
"""
Zotero Library Reorganizer for Research Domains
--------------------------------------------------
This script creates new topic-based folders in your Zotero library
and assigns relevant papers to them while preserving the original
folder structure.

Requirements:
- pyzotero package: pip install pyzotero
"""

import time
import argparse
import json
from pathlib import Path
from pyzotero import zotero

def load_collections_from_json(json_path):
    """
    Load and validate collections from a JSON file.
    
    Args:
        json_path: Path to the JSON file containing collection definitions
        
    Returns:
        list: List of collection definitions
        
    Raises:
        ValueError: If the JSON file is invalid or missing required fields
    """
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON file: {str(e)}")
    except FileNotFoundError:
        raise ValueError(f"JSON file not found: {json_path}")
    
    if 'collections' not in data:
        raise ValueError("JSON file must contain a 'collections' key")
    
    collections = data['collections']
    if not isinstance(collections, list):
        raise ValueError("'collections' must be a list")
    
    # Validate each collection
    for i, collection in enumerate(collections):
        if 'name' not in collection:
            raise ValueError(f"Collection at index {i} missing 'name' field")
        if 'papers' not in collection:
            raise ValueError(f"Collection at index {i} missing 'papers' field")
        if not isinstance(collection['papers'], list):
            raise ValueError(f"'papers' in collection {i} must be a list")
    
    return collections

def create_collections_hierarchy(zot, collections_data, pause_duration=0.3, verbose=True):
    """
    Create a hierarchy of collections in Zotero and assign papers to them.
    
    Args:
        zot: An initialized Zotero API client
        collections_data: List of collection definitions with name and paper keys
        pause_duration: Seconds to pause between API calls (avoid rate limiting)
        verbose: Whether to print detailed progress information
    
    Returns:
        dict: Statistics about created collections and assigned papers
    """
    stats = {
        "top_level_created": 0,
        "subcollections_created": 0,
        "papers_assigned": 0,
        "existing_collections_used": 0,
        "papers_not_found": 0,
        "assignment_failures": 0
    }
    
    # Get existing collections for reference
    if verbose:
        print("Fetching existing collections...")
    existing_collections = zot.collections()
    existing_collection_names = [c['data']['name'] for c in existing_collections]
    
    if verbose:
        print(f"Found {len(existing_collections)} existing collections")
    
    # Create new collections if they don't exist
    new_collection_keys = {}
    if verbose:
        print("\nCreating new topic-based collections...")
    
    # First, process collections with no "/" in name (top-level collections)
    for collection in [c for c in collections_data if "/" not in c["name"]]:
        collection_name = collection["name"]
        
        # Check if collection already exists
        if collection_name in existing_collection_names:
            if verbose:
                print(f" - Collection '{collection_name}' already exists, using existing collection")
            # Find the key of the existing collection
            for c in existing_collections:
                if c['data']['name'] == collection_name:
                    new_collection_keys[collection_name] = c['data']['key']
                    stats["existing_collections_used"] += 1
                    break
        else:
            # Create new collection
            if verbose:
                print(f" - Creating collection '{collection_name}'")
            new_collection = zot.create_collection([{"name": collection_name}])
            new_collection_keys[collection_name] = new_collection['successful']['0']['key']
            stats["top_level_created"] += 1
            
            # Pause briefly to avoid rate limiting
            time.sleep(pause_duration)
    
    # Then process collections with "/" in name (subcollections)
    for collection in [c for c in collections_data if "/" in c["name"]]:
        collection_name = collection["name"]
        parent_name, sub_name = collection_name.split("/", 1)
        
        # Make sure parent exists
        if parent_name not in new_collection_keys:
            if verbose:
                print(f" - Parent collection '{parent_name}' not found, skipping '{collection_name}'")
            continue
        
        parent_key = new_collection_keys[parent_name]
        
        # Check if subcollection already exists
        subcollection_exists = False
        subcollection_key = None
        
        # Get all subcollections of the parent
        subcollections = zot.collections_sub(parent_key)
        for sub in subcollections:
            if sub['data']['name'] == sub_name:
                subcollection_exists = True
                subcollection_key = sub['data']['key']
                break
        
        if subcollection_exists:
            if verbose:
                print(f" - Subcollection '{sub_name}' already exists under '{parent_name}', using existing collection")
            new_collection_keys[collection_name] = subcollection_key
            stats["existing_collections_used"] += 1
        else:
            # Create subcollection
            if verbose:
                print(f" - Creating subcollection '{sub_name}' under '{parent_name}'")
            new_sub = zot.create_collection([{
                "name": sub_name, 
                "parentCollection": parent_key
            }])
            new_collection_keys[collection_name] = new_sub['successful']['0']['key']
            stats["subcollections_created"] += 1
            
            # Pause briefly to avoid rate limiting
            time.sleep(pause_duration)
    
    # Now add papers to the new collections
    if verbose:
        print("\nAssigning papers to new collections...")
    for collection in collections_data:
        collection_name = collection["name"]
        
        if collection_name not in new_collection_keys:
            if verbose:
                print(f"Warning: Collection key for '{collection_name}' not found, skipping paper assignments")
            continue
            
        collection_key = new_collection_keys[collection_name]
        paper_keys = collection["papers"]
        
        if verbose:
            print(f"\nWorking on collection: {collection_name}")
        for paper_key in paper_keys:
            try:
                # Get the item to verify it exists
                item = zot.item(paper_key)
                if item:
                    title = item.get('data', {}).get('title', 'Untitled')
                    
                    # Add the item to the collection
                    try:
                        print("\n=== DEBUG LOGS ===")
                        print(f"Library type: {zot.library_type}")
                        print(f"Library ID: {zot.library_id}")
                        print(f"Collection key: {collection_key}")
                        print(f"Paper key: {paper_key}")
                        
                        # Get the current item
                        item = zot.item(paper_key)
                        if not item:
                            if verbose:
                                print(f" - Item {paper_key} not found in library")
                            stats["papers_not_found"] += 1
                            continue
                            
                        # Get the current collections
                        current_collections = item['data'].get('collections', [])
                        
                        # Add the new collection if not already present
                        if collection_key not in current_collections:
                            current_collections.append(collection_key)
                            item['data']['collections'] = current_collections
                            
                            # Update the item
                            result = zot.update_item(item)
                            
                            if result:
                                if verbose:
                                    print(f" - Added '{title}' [{paper_key}] to {collection_name}")
                                stats["papers_assigned"] += 1
                            else:
                                if verbose:
                                    print(f" - Failed to add '{title}' [{paper_key}] to {collection_name}")
                                stats["assignment_failures"] += 1
                        else:
                            if verbose:
                                print(f" - Item '{title}' [{paper_key}] already in {collection_name}")
                            stats["papers_assigned"] += 1
                            
                    except Exception as e:
                        print(f"\nException occurred: {str(e)}")
                        print(f"Exception type: {type(e)}")
                        if verbose:
                            print(f" - Error adding {paper_key} to collection: {str(e)}")
                        stats["assignment_failures"] += 1
                    
                    print("=== END DEBUG LOGS ===\n")
                    
                    # Pause briefly to avoid rate limiting
                    time.sleep(pause_duration)
                else:
                    if verbose:
                        print(f" - Item {paper_key} not found in library")
                    stats["papers_not_found"] += 1
            except Exception as e:
                if verbose:
                    print(f" - Error adding {paper_key} to collection: {e}")
                stats["assignment_failures"] += 1
    
    return stats


def print_stats(stats):
    """
    Print statistics about the collection creation process.
    
    Args:
        stats: Dictionary containing statistics
    """
    print("\n" + "="*50)
    print("Library Reorganization Statistics")
    print("="*50)
    
    print(f"- Created {stats['top_level_created']} new top-level collections")
    print(f"- Created {stats['subcollections_created']} new subcollections")
    print(f"- Used {stats['existing_collections_used']} existing collections")
    print(f"- Successfully assigned {stats['papers_assigned']} papers")
    if stats['papers_not_found'] > 0:
        print(f"- {stats['papers_not_found']} papers were not found in the library")
    if stats['assignment_failures'] > 0:
        print(f"- {stats['assignment_failures']} paper assignments failed")
    
    print("\nLibrary reorganization complete!")
    print("All papers remain in their original folders, and new topic-based folders have been created.")
    print("Note: Papers might appear in multiple collections as intended.")


def main():
    """
    Main function to parse arguments and run the reorganization.
    """
    parser = argparse.ArgumentParser(description='Reorganize a Zotero library with research domain collections')
    parser.add_argument('--api-key', required=True, help='Your Zotero API key')
    parser.add_argument('--library-id', required=True, help='Your Zotero user ID or group ID')
    parser.add_argument('--library-type', default='user', choices=['user', 'group'], 
                       help='Library type (user or group)')
    parser.add_argument('--collections-file', required=True, type=Path,
                       help='Path to JSON file containing collection definitions')
    parser.add_argument('--quiet', action='store_true', help='Suppress detailed progress output')
    parser.add_argument('--pause', type=float, default=0.3, 
                       help='Seconds to pause between API calls (default: 0.3)')
    args = parser.parse_args()
    
    # Load collections from JSON file
    try:
        collections = load_collections_from_json(args.collections_file)
    except ValueError as e:
        print(f"Error loading collections: {str(e)}")
        return 1
    
    # Initialize Zotero API connection
    zot = zotero.Zotero(args.library_id, args.library_type, args.api_key)
    
    # Create collections and add papers
    stats = create_collections_hierarchy(
        zot, 
        collections, 
        pause_duration=args.pause,
        verbose=not args.quiet
    )
    
    # Print stats
    print_stats(stats)
    return 0


if __name__ == "__main__":
    exit(main())