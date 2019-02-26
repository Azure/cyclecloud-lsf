from util import JsonStore
import sys

if not JsonStore(sys.argv[1], sys.argv[2])._lock():
    sys.exit(101)
