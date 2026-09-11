#!/usr/bin/env python
"""python scripts/export_history.py 002971 20260910 [outdir]"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tdxapi.cli import main
sys.exit(main(["history"] + sys.argv[1:]))
