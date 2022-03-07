# Textile parser

Parses textile files (dradis) to a LaTeX issue format.

## Setup

```
pip install -e .
```

## Usage

CLI usage:

```
python textile_parser.py test_files/issue.dradis -e test_files/evidence.dradis -l localhost
dradis_to_latex test_files/issue.dradis -e test_files/evidence.dradis -l localhost
```

For python usage see [text.py](test.py)
