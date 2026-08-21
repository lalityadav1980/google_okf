from pathlib import Path

import yaml

from xyz_okf.models import IssueCatalog


def load_issue_catalog(path: Path) -> IssueCatalog:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return IssueCatalog.model_validate(data)
