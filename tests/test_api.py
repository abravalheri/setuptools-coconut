from pathlib import Path
from textwrap import dedent

import pytest

from setuptools_coconut import api


def mkpath(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(repr(str(path)))
    return path


def mksrc(parent):
    src = Path(parent, "src")

    paths = [
        src / "pkg/__init__.coconut",
        src / "pkg/module1.coconut",
        src / "pkg/module2.coc",
        src / "pkg/module3.coco",
        src / "pkg/subpkg1/__init__.coconut",
        src / "pkg/subpkg1/data.txt",
        src / "pkg/subpkg2/__init__.py",
        src / "pkg/subpkg2/pymodule.py",
    ]

    return [mkpath(p) for p in paths]


class TestOtherFiles:
    def test_find_files(self, tmp_path):
        mksrc(tmp_path)
        other = api.OtherFiles(str(tmp_path), "src")

        src = Path(tmp_path, "src")
        expected = [
            src / "pkg/subpkg1/data.txt",
            src / "pkg/subpkg2/__init__.py",
            src / "pkg/subpkg2/pymodule.py",
        ]
        for f in expected:
            assert f.exists()
        assert other.files == list(map(str, expected))

    def test_link_or_copy(self, tmp_path):
        mksrc(tmp_path)
        build = Path(tmp_path, "build")
        others = api.OtherFiles(str(tmp_path), "src")
        given = list(others.link_or_copy(str(build)))

        expected = [
            build / "pkg/subpkg1/data.txt",
            build / "pkg/subpkg2/__init__.py",
            build / "pkg/subpkg2/pymodule.py",
        ]

        assert given == list(map(str, expected))

        print("build", list(build.glob("**/*")))
        for f in expected:
            print(f)
            print(f.parent)
            print(list(f.parent.glob("*")))
            assert f.exists()
            assert f.read_text() == repr(str(f)).replace("build", "src")


class CompileFiles:
    def test_default_src_target(self, pyproject):
        # Default config
        config = "[tool.coconut]"
        pyproject.write_text(config)
        project_path = pyproject.parent
        mksrc(project_path)
        included_files = list(api.compiled_files(project_path))

        expected = [
            "src/pkg/__init__.py",
            "src/pkg/module1.py",
            "src/pkg/module2.py",
            "src/pkg/module3.py",
            "src/pkg/subpkg1/__init__.py",
        ]
        assert included_files == expected
        assert not (project_path / "src" / "src").exists()

    def test_build_dir(self, pyproject):
        # Default config
        config = """\
        [tool.coconut]
        dest = "build"
        """
        pyproject.write_text(dedent(config))
        project_path = pyproject.parent
        mksrc(project_path)
        included_files = list(api.compiled_files(project_path))

        expected = [
            "build/src/pkg/__init__.py",
            "build/src/pkg/module1.py",
            "build/src/pkg/module2.py",
            "build/src/pkg/module3.py",
            "build/src/pkg/subpkg1/__init__.py",
            # Files outside of build are copied
            "build/src/pkg/subpkg1/data.txt",
            "build/src/pkg/subpkg2/__init__.py",
            "build/src/pkg/subpkg2/pymodule.py",
        ]
        assert included_files == expected

    def test_build_dir_as_src(self, pyproject):
        # Default config
        config = """\
        [tool.coconut]
        dest = "src"
        """
        pyproject.write_text(dedent(config))
        project_path = pyproject.parent
        mksrc(project_path)
        with pytest.raises(ValueError) as exc:
            list(api.compiled_files(project_path))
        msg = str(exc.value).replace("`", "")
        assert "avoid recursion" in msg
        assert "dest cannot be the same as src" in msg
