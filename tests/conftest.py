import sys
from pathlib import Path

# Get the project root directory
project_root = Path(__file__).parent.parent.absolute()

# Add the project root and the magic512bot directory to the Python path
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "magic512bot"))
