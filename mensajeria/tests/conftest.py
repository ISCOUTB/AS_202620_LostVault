import sys
from pathlib import Path

# Permite `import mensajeria` sin instalar el paquete
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
