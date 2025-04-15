# Zotero Library Reorganizer

A mostly vibe-coded to create topic-based collections in your Zotero library and assign papers to them while preserving the original folder structure.

USE AT YOUR OWN RISK.

## Generating Research Collections

I used Claude with the Zotero MCP to actually generate research collections for me (I was bad at being consistent about tagging and organizing). I included portions of the prompts in `prompts.md`.


## Requirements

- Python 3.6+
- pyzotero package: `pip install pyzotero`

## Usage

1. Create a JSON file defining your collections (see template below)
2. Run the script with your Zotero API credentials and the JSON file:

```bash
python main.py --api-key YOUR_API_KEY --library-id YOUR_LIBRARY_ID --collections-file collections.json
```

### JSON Format

The JSON file should follow this structure:

```json
{
    "collections": [
        {
            "name": "Category 1",
            "papers": [
                "PAPER1KEY",  # Paper Title 1
                "PAPER2KEY"   # Paper Title 2
            ]
        },
        {
            "name": "Category 1/Subcategory 1",
            "papers": [
                "PAPER1KEY",  # Paper Title 1
                "PAPER3KEY"   # Paper Title 3
            ]
        }
    ]
}
```

- `name`: The name of the collection. Use "/" to create subcollections
- `papers`: List of Zotero item keys to add to the collection
- Comments (starting with #) are optional and can be used to document paper titles

### Command Line Arguments

- `--api-key`: Your Zotero API key (required)
- `--library-id`: Your Zotero user ID or group ID (required)
- `--library-type`: Library type (user or group, default: user)
- `--collections-file`: Path to JSON file containing collection definitions (required)
- `--quiet`: Suppress detailed progress output
- `--pause`: Seconds to pause between API calls (default: 0.3)

## Example

1. Create a collections.json file:
```json
{
    "collections": [
        {
            "name": "Category 1",
            "papers": [
                "ID",  # A paper
            ]
        },
        {
            "name": "Category 2",
            "papers": [
                "ID",  # A paper
            ]
        }
    ]
}
```

2. Run the script:
```bash
python main.py --api-key API_KEY --library-id ID --collections-file COLLECTIONS_FILE
```