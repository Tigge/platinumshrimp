#!/usr/bin/env python3
"""
Standalone manual test script for the Tyda translation plugin.

This script is NOT part of the IRC bot plugin itself; it is a helper tool
to manually verify translation results from tyda.se using the plugin's
internal logic.

Usage:
    poetry run python3 plugins/tyda/lookup.py <word>

Example:
    $ poetry run python3 plugins/tyda/lookup.py vårdpersonal
    nursing staff [ medicin ]
    health personnel [ medicin ]
    care staff nursing auxiliaries [ medicin ]
"""

import sys
import argparse
import os

# Add the project root to sys.path so we can import 'plugins' and 'plugin'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from plugins.tyda.tyda import Tyda


def main():
    parser = argparse.ArgumentParser(description="Standalone Tyda lookup tool")
    parser.add_argument("query", help="The word to translate")
    args = parser.parse_args()

    # We patch Tyda to avoid plugin.Plugin.__init__ which starts ZMQ
    import plugin

    original_init = plugin.Plugin.__init__
    plugin.Plugin.__init__ = lambda self, name: None

    try:
        tyda = Tyda()
        results = tyda.lookup(args.query)
        if not results:
            print(f"No results found for '{args.query}'")
        else:
            for res in results:
                print(res)
    finally:
        # Restore original init if needed
        plugin.Plugin.__init__ = original_init


if __name__ == "__main__":
    main()
