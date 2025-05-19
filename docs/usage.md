# Usage Guide for Raindrop Import Scripts

This document provides detailed usage examples for the import scripts included in this project.

## Table of Contents
- [Installation](#installation)
- [Evernote Import](#evernote-import)
  - [Command-line Options](#evernote-command-line-options)
  - [Examples](#evernote-examples)
- [Pocket Import](#pocket-import)
  - [Command-line Options](#pocket-command-line-options)
  - [Examples](#pocket-examples)
- [Chrome Bookmarks Import](#chrome-bookmarks-import)
  - [Command-line Options](#chrome-command-line-options)
  - [Examples](#chrome-examples)
- [Firefox Bookmarks Import](#firefox-bookmarks-import)
  - [Command-line Options](#firefox-command-line-options)
  - [Examples](#firefox-examples)
- [Importing into Raindrop.io](#importing-into-raindropio)
- [Troubleshooting](#troubleshooting)

## Installation

Before using the scripts, make sure you have installed the project dependencies:

```bash
# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate the Poetry shell
poetry shell
```

## Evernote Import

The Evernote import script (`evernote/enex2csv.py`) converts Evernote export files (.enex) to CSV format that can be imported into Raindrop.io.

### Evernote Command-line Options

```
usage: enex2csv.py [-h] --input-file ENEXFILE --output-file CSVFILE [--use-markdown] [--verbose]

Convert Evernote ENEX file to CSV

options:
  -h, --help            show this help message and exit
  --input-file ENEXFILE
                        Input ENEX file path
  --output-file CSVFILE
                        Output CSV file path
  --use-markdown        Convert note content to Markdown
  --verbose             Enable verbose logging
```

### Evernote Examples

**Basic conversion:**
```bash
python evernote/enex2csv.py --input-file export.enex --output-file evernote.csv
```

**Convert note content to Markdown:**
```bash
python evernote/enex2csv.py --input-file export.enex --output-file evernote.csv --use-markdown
```

**Enable verbose logging:**
```bash
python evernote/enex2csv.py --input-file export.enex --output-file evernote.csv --verbose
```

**Process a large ENEX file:**
```bash
python evernote/enex2csv.py --input-file large_export.enex --output-file evernote.csv --use-markdown
```

## Pocket Import

The Pocket import script (`pocket/pocket2csv.py`) converts Pocket HTML export files to CSV format that can be imported into Raindrop.io.

### Pocket Command-line Options

```
usage: pocket2csv.py [-h] --input-file HTMLFILE --output-file CSVFILE

Convert Pocket HTML file to CSV

options:
  -h, --help            show this help message and exit
  --input-file HTMLFILE
                        Input HTML file path
  --output-file CSVFILE
                        Output CSV file path
```

### Pocket Examples

**Basic conversion:**
```bash
python pocket/pocket2csv.py --input-file ril_export.html --output-file pocket.csv
```

**Using a different input file name:**
```bash
python pocket/pocket2csv.py --input-file pocket_export.html --output-file pocket.csv
```

## Chrome Bookmarks Import

The Chrome bookmarks import script (`chrome/chrome2csv.py`) converts Chrome bookmarks JSON export files to CSV format that can be imported into Raindrop.io.

### Chrome Command-line Options

```
usage: chrome2csv.py [-h] --input-file JSONFILE --output-file CSVFILE [--log-file LOGFILE] [--dry-run]

Convert Chrome bookmarks JSON file to CSV

options:
  -h, --help            show this help message and exit
  --input-file JSONFILE
                        Input JSON file path (typically 'Bookmarks' file from Chrome)
  --output-file CSVFILE
                        Output CSV file path
  --log-file LOGFILE    Log file path (optional)
  --dry-run             Validate without writing files
```

### Chrome Examples

**Basic conversion:**
```bash
python chrome/chrome2csv.py --input-file Bookmarks --output-file chrome.csv
```

**Using a different input file name:**
```bash
python chrome/chrome2csv.py --input-file chrome_bookmarks.json --output-file chrome.csv
```

**With logging to a file:**
```bash
python chrome/chrome2csv.py --input-file Bookmarks --output-file chrome.csv --log-file chrome_import.log
```

**Dry run (validate without writing files):**
```bash
python chrome/chrome2csv.py --input-file Bookmarks --output-file chrome.csv --dry-run
```

## Firefox Bookmarks Import

The Firefox bookmarks import script (`firefox/firefox2csv.py`) converts Firefox bookmarks JSON export files to CSV format that can be imported into Raindrop.io.

### Firefox Command-line Options

```
usage: firefox2csv.py [-h] --input-file JSONFILE --output-file CSVFILE [--log-file LOGFILE] [--dry-run]

Convert Firefox bookmarks JSON file to CSV

options:
  -h, --help            show this help message and exit
  --input-file JSONFILE
                        Input JSON file path (exported from Firefox bookmarks)
  --output-file CSVFILE
                        Output CSV file path
  --log-file LOGFILE    Log file path (optional)
  --dry-run             Validate without writing files
```

### Firefox Examples

**Basic conversion:**
```bash
python firefox/firefox2csv.py --input-file bookmarks-2023-05-18.json --output-file firefox.csv
```

**Using a different input file name:**
```bash
python firefox/firefox2csv.py --input-file firefox_bookmarks.json --output-file firefox.csv
```

**With logging to a file:**
```bash
python firefox/firefox2csv.py --input-file bookmarks-2023-05-18.json --output-file firefox.csv --log-file firefox_import.log
```

**Dry run (validate without writing files):**
```bash
python firefox/firefox2csv.py --input-file bookmarks-2023-05-18.json --output-file firefox.csv --dry-run
```

## Importing into Raindrop.io

After generating the CSV files, you can import them into Raindrop.io:

1. Log in to your Raindrop.io account
2. Go to Settings > Import
3. Select "Import from CSV file"
4. Upload the CSV file generated by one of the scripts
5. Follow the on-screen instructions to complete the import

Note: Raindrop.io has a file size limit for imports. If your CSV file is too large, you may need to split it into smaller files.

## Troubleshooting

**Issue: Script fails with "File not found" error**
- Make sure the input file path is correct
- Check if you have read permissions for the input file
- Try using an absolute path instead of a relative path

**Issue: Output CSV file is empty or incomplete**
- Check if the input file is valid (proper ENEX or Pocket HTML format)
- For Evernote, try without the `--use-markdown` option
- Check if you have write permissions for the output directory

**Issue: Import to Raindrop.io fails**
- Verify the CSV file format is correct
- Check if the file size is within Raindrop.io's limits
- Try splitting the file into smaller chunks

**Issue: Special characters are not displayed correctly**
- Make sure your input files are properly encoded (UTF-8 recommended)
- Check if your terminal supports the character encoding
