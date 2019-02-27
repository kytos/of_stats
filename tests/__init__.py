"""Tests from of_stats napp."""

import sys
import os
from pathlib import Path

if 'VIRTUAL_ENV' in os.environ:
    BASE_ENV = Path(os.environ['VIRTUAL_ENV'])
else:
    BASE_ENV = Path('/')

OF_STATS_PATH = BASE_ENV / '/var/lib/kytos/'

sys.path.insert(0, str(OF_STATS_PATH))
