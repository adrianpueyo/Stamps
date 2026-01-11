"""Compatibility wrapper for the Stamps tool.

This module re-exports the public API from stamps_core so existing Nuke callbacks
and user scripts that import `stamps` continue to work.
"""

from stamps_core import *  # noqa: F401,F403

import integration

integration.initialize()
