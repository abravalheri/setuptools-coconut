from itertools import chain, cycle
from pathlib import Path
from typing import Iterable

import pytest
from setuptools import build_meta as setuptools

from setuptools_coconut import debug
from setuptools_coconut.config import CoconutConfig, ValidationError

from .helpers import list_zip, rmpath

HERE = Path(__file__).parent
EXAMPLES = HERE / "examples"
INVALID_EXAMPLES = HERE / "invalid-examples"


def examples():
    return [str(f.relative_to(EXAMPLES)) for f in EXAMPLES.glob("*")]


def invalid_examples():
    return [str(f.relative_to(INVALID_EXAMPLES)) for f in INVALID_EXAMPLES.glob("*")]


def coconut_files(path: Path) -> Iterable[Path]:
    cfg_path = path / "pyproject.toml"
    if cfg_path.exists():
        cfg = CoconutConfig.from_file(cfg_path) or CoconutConfig()
    else:
        cfg = CoconutConfig()

    for src in cfg.src:
        src_path = path / src
        for p in src_path.glob("**/*.coco"):
            yield p.relative_to(src_path)


def other_files(path: Path) -> Iterable[Path]:
    src_path = path / "src"
    for p in src_path.glob("**/*"):
        if p.is_file() and p.suffix != ".coco":
            yield p.relative_to(src_path)


def prepare_project(path: Path):
    # Remove old files that might interfere with setuptools
    rmpath(path / "dist")
    rmpath(path / "build/lib")
    build_dirs = chain(
        path.glob("build/bdist*"),
        path.glob("build/**/*.egg-info"),
        path.glob("build/**/*.dist-info"),
    )
    for p in build_dirs:
        rmpath(p)

    # Make sure target directories exist
    (path / "build/src").mkdir(parents=True, exist_ok=True)
    (path / "dist").mkdir(parents=True, exist_ok=True)
    return path


def build_project(path, monkeypatch, set_debug):
    with monkeypatch.context() as m:
        m.chdir(path)
        if set_debug:
            m.setattr(debug, "DEBUG", True)
        # For some reason some of the projects need to be build twice,
        # so setuptools end up including all the files
        # but `python -m build` seems to get it right
        setuptools.build_wheel(path / "dist")
        setuptools.build_wheel(path / "dist")


@pytest.mark.parametrize("example, set_debug", zip(examples(), cycle([False, True])))
def test_valid_examples(example, set_debug, monkeypatch):
    path = Path(EXAMPLES, example)
    prepare_project(path)
    build_project(path, monkeypatch, set_debug)

    distibutions = list(path.glob("dist/*.whl"))
    assert distibutions
    distribution_files = set(list_zip(distibutions[0]))
    files = {str(p.with_suffix(".py")) for p in coconut_files(path)}
    files |= {str(p) for p in other_files(path)}
    try:
        assert distribution_files >= files
    except AssertionError:
        print("~_" * 40)
        print("Missing files:\n")
        print("\n".join(sorted(files - distribution_files)))
        print("~_" * 40)
        raise


@pytest.mark.parametrize(
    "example, set_debug", zip(invalid_examples(), cycle([False, True]))
)
def test_invalid_examples(example, set_debug, monkeypatch):
    path = Path(INVALID_EXAMPLES, example)
    prepare_project(path)
    try:
        build_project(path, monkeypatch, set_debug)
        # If the project manages to be build, no coconut file should be compiled
        distibutions = list(path.glob("dist/*.whl"))
        distribution_files = set(list_zip(distibutions[0]))
        files = {str(p.with_suffix(".py")) for p in coconut_files(path)}
        compiled_and_included = distribution_files & files
        try:
            assert len(compiled_and_included) == 0
        except AssertionError:
            print("~_" * 40)
            print("The following files should not have been compiled:\n")
            print("\n".join(sorted(compiled_and_included)))
            print("~_" * 40)
            raise
    except ValidationError:
        # Invalid files are expected to have validation errors
        pass
