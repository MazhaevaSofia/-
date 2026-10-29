#!/bin/bash
cd "$(dirname "$0")"
python3 -m pip install --quiet pygame numpy
python3 main.py
