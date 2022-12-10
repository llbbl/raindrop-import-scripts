# raindrop-import-scripts
A collection of import scripts for raindrop.io


## Evernote import

This is a fork of another project [YuriyGuts/enex2csv](https://github.com/YuriyGuts/enex2csv) modified to work with raindrop.io

Importing enex files directly into raindrop.io is a bit tricky. The filesize limitations are the biggest problem. It's better to just convert to csv, then import to raindrop. 

Example Usage:
```bash
python enex2csv.py --input-file export.enex --output-file evernote.csv --use-markdown
```

## Pocket import

