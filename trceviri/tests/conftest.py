import sys
from pathlib import Path

# testler hangi klasörden çalıştırılırsa çalıştırılsın 'trceviri' paketi bulunsun
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
