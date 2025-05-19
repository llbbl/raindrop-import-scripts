# raindrop-import-scripts

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/llbbl/raindrop-import-scripts/graphs/commit-activity)

A collection of import scripts for raindrop.io

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
4. Run the scripts using Poetry:
   ```bash
   poetry run python evernote/enex2csv.py --input-file export.enex --output-file evernote.csv
   ```
   Or activate the Poetry shell first:
   ```bash
   poetry shell
   python evernote/enex2csv.py --input-file export.enex --output-file evernote.csv
   ```
5. See below for specific examples

## Evernote import

This is a fork of another project [YuriyGuts/enex2csv](https://github.com/YuriyGuts/enex2csv) modified to work with raindrop.io

Importing enex files directly into raindrop.io is a bit tricky. The filesize limitations are the biggest problem. It's better to just convert to csv, then import to raindrop. 

Example Usage:
```bash
python enex2csv.py --input-file export.enex --output-file evernote.csv --use-markdown
```

## Pocket import

Wrote this script to import my pocket list into raindrop.io. The script pareses the HTML export file and creates a csv file that can be imported.

In order to get your exported HTML file from pocket, go to [https://getpocket.com/export](https://getpocket.com/export) and download the file. Their help page about the export can be found [here](https://help.getpocket.com/article/1015-exporting-your-pocket-list). 

Example Usage:
```bash
python pocket2csv.py --input-file ril_export.html --output-file pocket.csv
```
