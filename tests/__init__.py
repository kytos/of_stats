<<<<<<< Updated upstream
=======
"""Tests from of_stats napp."""

>>>>>>> Stashed changes
import sys
import os
from pathlib import Path

if 'VIRTUAL_ENV' in os.environ:
    BASE_ENV = Path(os.environ['VIRTUAL_ENV'])
else:
    BASE_ENV = Path('/')

<<<<<<< Updated upstream
#STATUS_NAPP_PATH = BASE_ENV / '/var/lib/kytos/napps/..'

STATUS_NAPP_PATH = str(BASE_ENV) + '/var/lib/kytos/napps/kytos/'

sys.path.insert(0, STATUS_NAPP_PATH)
=======
OF_STATS_PATH = BASE_ENV / '/var/lib/kytos/napps/..'

sys.path.insert(0, str(OF_STATS_PATH))
>>>>>>> Stashed changes
