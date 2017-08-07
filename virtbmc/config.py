import os.path
from virtbmc import utils

BASE_DIR = utils.dirname(__file__, 1)

# WORKSPACE used to store QEMU/BMC config/script files
WORKSPACE = os.path.join(BASE_DIR, 'workspace')

DB_FILE = os.path.join(WORKSPACE, 'virtbmc.db')
