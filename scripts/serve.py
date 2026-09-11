#!/usr/bin/env python
"""python scripts/serve.py --pid <PID> --port 8712"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tdxapi.server import main
sys.exit(main(sys.argv[1:]) or 0)
