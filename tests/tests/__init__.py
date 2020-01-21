"""Module to test the napp kytos/of_stats."""
import os
import sys
from pathlib import Path

BASE_ENV = Path(os.environ.get('VIRTUAL_ENV', '/'))

OF_STATS_PATH = BASE_ENV / 'var/lib/of_stats/napps/..'

sys.path.insert(0, str(OF_STATS_PATH))
