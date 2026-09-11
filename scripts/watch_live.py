#!/usr/bin/env python
"""python scripts/watch_live.py 000001 --seconds 30"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tdxapi.cli import main
sys.exit(main(["live"] + sys.argv[1:]))
