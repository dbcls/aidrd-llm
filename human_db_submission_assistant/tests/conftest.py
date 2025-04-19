import sys
import os
from pathlib import Path

# Add the parent directory to sys.path to make imports work
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
