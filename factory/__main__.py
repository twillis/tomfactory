"""Lets `python -m factory ...` run the commands."""
import sys

from factory.cli import main

sys.exit(main(sys.argv[1:]))
