jmlr-proceedings-cmt
====================

Publication chair's tool for creating JMLR W&amp;CP proceedings
from CMT information and PDF submission files.

Copyright (c) 2014, Antti Honkela

Used for AISTATS 2014, feel free to reuse at your own risk.

Please edit the configuration section at the beginning of the script
before you start.

Requirements:
- Un*x-like OS
- LaTeX
- pdfinfo
- unidecode Python package

Functionality:
- reads CMT camera ready paper information
- reads CMT user data to resolve ambiguous firstname/lastname splits
- uses 'pdfinfo' to get paper information (number of pages)
- generates LaTeX files that add page numbers and include every page of the
  submitted files separately and compiles them
- writes a BibTeX file according to JMLR W&amp;CP spec
