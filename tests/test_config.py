from pathlib import Path
from textwrap import dedent

import pytest

from setuptools_coconut import debug
from setuptools_coconut.config import CoconutConfig


def test_build_paths(pyproject):
    example = """\
    [tool.coconut]
    src = ["src", "pkg"]
    """
    pyproject.write_text(dedent(example))
    cfg = CoconutConfig.from_file(pyproject)
    assert cfg.build_paths() == {"src": "src", "pkg": "pkg"}

    example = """\
    [tool.coconut]
    src = ["pkg", "src"]
    dest = "build"
    """
    pyproject.write_text(dedent(example))
    cfg = CoconutConfig.from_file(pyproject)
    assert cfg.build_paths() == {"src": "build/src", "pkg": "build/pkg"}


def test_args(pyproject):
    cfg = CoconutConfig()
    assert cfg.as_cli_args() == ["--target", "3.6", "-j", "sys", "--strict"]

    example = """\
    [tool.coconut]
    target = "3.8"
    mypy = true
    strict = false
    tco = false
    wrap = false
    processes = 2
    argv = ["--force"]
    """
    pyproject.write_text(dedent(example))
    cfg = CoconutConfig.from_file(pyproject)
    assert cfg.as_cli_args() == [
        "--target",
        "3.8",
        "-j",
        "2",
        "--no-tco",
        "--no-wrap",
        "--mypy",
        "--force",
    ]


def test_same_src_and_dest(pyproject):
    example = """\
    [tool.coconut]
    src = ["pkg", "src"]
    dest = "src"
    """
    pyproject.write_text(dedent(example))
    with pytest.raises(ValueError) as exc:
        CoconutConfig.from_file(pyproject)
    msg = str(exc.value).replace("`", "")
    assert "avoid recursion" in msg
    assert "dest cannot be the same as src" in msg


def test_invalid_config(pyproject):
    example = """\
    [tool.coconut]
    asdf = 42
    """
    pyproject.write_text(dedent(example))
    with pytest.raises(ValueError) as exc:
        CoconutConfig.from_file(pyproject)
    msg = str(exc.value).replace("`", "")
    assert "extra fields not permitted" in msg


def test_non_existing_file(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(debug, "DEBUG", True)
    pyproject = Path(tmp_path, "no-file")
    assert CoconutConfig.from_file(pyproject) is None
    out, err = capsys.readouterr()
    assert "no configuration file" in (out + err).lower()


def test_non_existing_table(pyproject, capsys, monkeypatch):
    monkeypatch.setattr(debug, "DEBUG", True)
    assert CoconutConfig.from_file(pyproject) is None
    out, err = capsys.readouterr()
    assert "no table [tool.coconut] found" in (out + err).lower()
