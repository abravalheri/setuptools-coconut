from pathlib import Path

import pytest


@pytest.fixture
def pyproject(tmp_path):
    file = Path(tmp_path, "pyproject.toml")
    file.touch()
    return file
