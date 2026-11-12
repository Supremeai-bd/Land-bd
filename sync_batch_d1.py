#!/usr/bin/env python3
"""Deprecated unsafe partial loader; route all checks to the safe read-only planner."""
from sync_to_d1 import main

if __name__ == "__main__":
    raise SystemExit(main())
