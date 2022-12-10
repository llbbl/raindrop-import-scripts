# raindrop-import-scripts
A collection of import scripts for raindrop.io

## Installation
1. Clone this repository
2. Install the dependencies: pipenv install
3. Run the scripts, see below for specific examples

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


