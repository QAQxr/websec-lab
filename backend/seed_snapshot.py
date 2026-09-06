import json

from backend.config import Settings
from backend.repositories.lab_repository import LabRepository


if __name__ == "__main__":
    snapshot = LabRepository(Settings.from_env()).seed_snapshot()
    print(json.dumps(snapshot, sort_keys=True, separators=(",", ":")))
