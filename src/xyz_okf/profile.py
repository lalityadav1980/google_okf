from pathlib import Path

import yaml

from xyz_okf.models import ProfileDefinition


def load_profile(path: Path) -> ProfileDefinition:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return ProfileDefinition.model_validate(data)
