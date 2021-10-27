from pathlib import Path
from typing import Iterable, List
from zipfile import ZipFile

import pytest
from setuptools import build_meta as setuptools

from setuptools_coconut.config import CoconutConfig

HERE = Path(__file__).parent
EXAMPLES = HERE / "examples"


def examples():
    return [str(f.relative_to(EXAMPLES)) for f in EXAMPLES.glob("*")]


def coconut_files(path: Path) -> Iterable[Path]:
    cfg = CoconutConfig.from_file(path / "pyproject.toml")
    for src in cfg.src:
        src_path = path / src
        for p in src_path.glob("**/*.coco"):
            yield p.relative_to(src_path)


def other_files(path: Path) -> Iterable[Path]:
    src_path = path / "src"
    for p in src_path.glob("**/*"):
        if p.is_file() and p.suffix != ".coco":
            yield p.relative_to(src_path)


def list_zip(p: Path) -> List[str]:
    with ZipFile(str(p), "r") as zipfile:
        return zipfile.namelist()


@pytest.mark.parametrize("example", examples())
def test_examples(example, monkeypatch):
    path = Path(EXAMPLES, example)
    (path / "build" / "src").mkdir(parents=True, exist_ok=True)
    (path / "dist").mkdir(parents=True, exist_ok=True)
    with monkeypatch.context() as m:
        m.chdir(path)
        m.setenv("SETUPTOOLS_COCONUT_DEBUG", "1")
        setuptools.build_wheel(path / "dist")
    distibutions = list(path.glob("dist/*.whl"))
    assert distibutions
    distribution_files = set(list_zip(distibutions[0]))
    files = {str(p.with_suffix(".py")) for p in coconut_files(path)}
    files |= {str(p) for p in other_files(path)}
    try:
        assert distribution_files >= files
    except AssertionError:
        print("~_" * 40)
        print("Missing files:\n", "\n".join(sorted(files - distribution_files)))
        print("~_" * 40)
        raise
