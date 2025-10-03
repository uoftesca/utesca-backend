# UTESCA Backend API
import sys
from pathlib import Path

# Add src directory to Python path so imports work when running from src/
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
