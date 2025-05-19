# raindrop-import-scripts

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/llbbl/raindrop-import-scripts/graphs/commit-activity)

A collection of import scripts for raindrop.io bookmark manager. Includes tools to convert various bookmark formats to CSV and directly import into Raindrop.io using their API.

## Installation
1. Clone this repository
2. Install Poetry (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```
3. Install the dependencies:
   ```bash
   poetry install
   ```
4. Run the unified CLI using Poetry:
   ```bash
   poetry run python raindrop_import.py [source] [options]
   ```
   Or activate the Poetry shell first:
   ```bash
   poetry shell
   python raindrop_import.py [source] [options]
   ```
5. See below for specific examples

## Unified CLI

The unified CLI provides a single entry point for all import sources:

```bash
python raindrop_import.py [source] [options]
```

Available sources:
- `evernote`: Import from Evernote ENEX files
- `pocket`: Import from Pocket HTML export files
- `chrome`: Import from Chrome bookmarks JSON files
- `firefox`: Import from Firefox bookmarks JSON files
- `raindrop-api`: Import directly to Raindrop.io using their API

For help with a specific source:
```bash
python raindrop_import.py [source] --help
```

## Configuration

You can configure the import scripts in three ways, in order of precedence:

1. **Command-line arguments**: Highest precedence, overrides all other settings
2. **Configuration file**: YAML file with default settings
3. **Environment variables**: Loaded from a `.env` file

### Configuration File

Create a `raindrop_import.yaml` file in the current directory or `~/.raindrop_import.yaml` in your home directory:

```yaml
global:
  log-file: raindrop_import.log
  dry-run: false

pocket:
  input-file: pocket_export.html
  output-file: pocket.csv

raindrop-api:
  api-token: your_api_token_here
  collection-id: 0
  batch-size: 50
```

### Environment Variables

Create a `.env` file in the current directory or `~/.raindrop_import.env` in your home directory:

```
# Global settings
RAINDROP_LOG_FILE=raindrop_import.log
RAINDROP_DRY_RUN=false

# Raindrop API settings
RAINDROP_API_TOKEN=your_api_token_here
```

See `.env.example` for more examples.

## Import Sources

### Raindrop API Import

Import bookmarks directly into Raindrop.io using their API:

```bash
# Using OAuth authentication (recommended)
python raindrop_import.py raindrop-api --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET --input-file bookmarks.csv --collection-id 0

# Using API token (deprecated)
python raindrop_import.py raindrop-api --api-token YOUR_API_TOKEN --input-file bookmarks.csv --collection-id 0
```

Authentication Options:
- `--client-id`: Your Raindrop.io OAuth client ID (recommended)
- `--client-secret`: Your Raindrop.io OAuth client secret (recommended)
- `--api-token`: Your Raindrop.io API token (deprecated)

Other Options:
- `--input-file`: CSV file with bookmarks to import (required)
- `--collection-id`: Raindrop.io collection ID to import into (default: 0 for Unsorted)
- `--batch-size`: Number of bookmarks to import in each batch (default: 50)
- `--dry-run`: Validate imports without sending to API

To get OAuth credentials, go to [Raindrop.io Developer Settings](https://app.raindrop.io/settings/integrations) and create a new app. You'll need both the client ID and client secret for OAuth authentication.

### Evernote Import

Import bookmarks from Evernote ENEX files:

```bash
python raindrop_import.py evernote --input-file export.enex --output-file evernote.csv --use-markdown
```

Options:
- `--input-file`: ENEX file to import (required)
- `--output-file`: CSV file to write (required)
- `--use-markdown`: Convert notes to Markdown format (optional)
- `--dry-run`: Validate imports without writing files

Importing ENEX files directly into raindrop.io is a bit tricky due to filesize limitations. It's better to convert to CSV first, then import to Raindrop.io.

This functionality is based on [YuriyGuts/enex2csv](https://github.com/YuriyGuts/enex2csv) modified to work with Raindrop.io.

### Pocket Import

Import bookmarks from Pocket HTML export files:

```bash
python raindrop_import.py pocket --input-file ril_export.html --output-file pocket.csv
```

Options:
- `--input-file`: HTML file to import (required)
- `--output-file`: CSV file to write (required)
- `--dry-run`: Validate imports without writing files

In order to get your exported HTML file from pocket, go to [https://getpocket.com/export](https://getpocket.com/export) and download the file. Their help page about the export can be found [here](https://help.getpocket.com/article/1015-exporting-your-pocket-list).
