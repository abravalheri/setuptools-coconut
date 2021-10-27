import os
import sys
from functools import lru_cache
from glob import glob
from os.path import abspath, dirname, exists, islink, join, relpath
from shutil import copy2
from subprocess import STDOUT, CalledProcessError, check_output
from typing import Iterable, List, Optional

from . import debug
from .config import DEFAULT_CONFIG_FILE, CoconutConfig, ValidationError

EXECUTABLE = (sys.executable, "-m", "coconut")
PROJECT_MARKERS = ("pyproject.toml", "setup.cfg", ".git", ".hg")
COCONUT_EXTENSIONS = (".coco", ".coconut", ".coc")


def discover_root(starting_point: Optional[str] = None) -> str:
    """Find the project root based in the existence of one of the files in
    :obj:`PROJECT_MARKERS`.
    """
    current = abspath(starting_point or os.getcwd())
    parent = None

    while current != parent:
        # current == parent => root directory
        if any(exists(join(current, m)) for m in PROJECT_MARKERS):
            return current

        parent = dirname(current)

    return current


@lru_cache()
def compile(project_root: str, config: CoconutConfig) -> Iterable[str]:
    """Compile the available ``.coco`` files according to ``config``
    and returns a list of locations where the compiled Python files were
    created.
    """
    opts = config.as_cli_args()
    for src in config.src:
        dest = config.build_path(src)
        dest_root = join(project_root, config.build_path(src))
        src_root = join(project_root, src)
        debug.print("coconut", src, dest, *opts)
        run_cmd([*EXECUTABLE, src_root, dest_root, *opts])
        yield abspath(dest).rstrip(os.pathsep)


def compiled_files(path: str = "") -> Iterable[str]:
    """Function responsible for integrating with ``setuptools``.

    Here we take advantage of the  ``setuptools.file_finders`` entry point
    to include the compiled files into the distribution.
    Although this hook was originally thought for being used with revision
    control systems, it is quite useful for generated files.

    For more information, see `setuptools user guide on extensions
    <https://setuptools.pypa.io/en/latest/userguide/extension.html#adding-support-for-revision-control-systems>`_.
    """  # noqa
    root = discover_root()
    debug.print(f"Detected root directory: {root}")
    config = CoconutConfig.from_file(join(root, DEFAULT_CONFIG_FILE))
    if config is None:
        debug.print("Skipping ...")
        return

    path = path or "."
    abs_path = abspath(path).rstrip(os.pathsep).replace(os.pathsep, "/")
    debug.print(f"Directory from setuptools integration: {abs_path}")
    for compiled_path in compile(root, config):
        if compiled_path.replace(os.pathsep, "/").startswith(abs_path):
            for file in glob(join(compiled_path, "**", "*.py")):
                yield debug.inspect(relpath(file, path))
        else:
            compiled_relpath = relpath(compiled_path, path)
            debug.print(f"{compiled_relpath!r} should be inside {abs_path!r}")

    # We need to move non-compiled files to the build dir also
    # so users can use "package_data"
    for src in config.src:
        other_files = OtherFiles(root, src)
        for file in other_files.link_or_copy(config.build_path(src)):
            if file.replace(os.pathsep, "/").startswith(abs_path):
                yield debug.inspect(relpath(file, path))


class OtherFiles:
    def __init__(
        self, project_root: str, parent_dir: str, coconut_extensions=COCONUT_EXTENSIONS
    ):
        self._root = project_root
        self._parent = join(project_root, parent_dir)
        self._files: Optional[List[str]] = None
        self._ext = coconut_extensions
        self._os_supports_symlink: Optional[bool] = None
        self._coconut_extensions = coconut_extensions

    @property
    def files(self) -> List[str]:
        if self._files is None:
            res: List[str] = []
            for directory, _, files in os.walk(self._parent):
                res.extend(
                    join(directory, f)
                    for f in files
                    if not any(f.endswith(e) for e in self._coconut_extensions)
                )
            self._files = res
        return self._files

    def _link_or_copy_file(self, orig: str, dest: str):
        root = self._root

        os.makedirs(dirname(dest), exist_ok=True)
        if self._os_supports_symlink is False:  # pragma: no cover
            action = "COPY"
            copy2(orig, dest)
        else:
            action = "LINK"
            try:
                if islink(dest):
                    os.unlink(dest)
                os.symlink(orig, dest)
                self._os_supports_symlink = True
            except OSError:  # pragma: no cover
                self._os_supports_symlink = False
                action = "COPY"
                copy2(orig, dest)

        debug.lazy(lambda: f"{action}: {relpath(orig, root)} => {relpath(dest, root)}")
        return dest

    def link_or_copy(self, other_dir: str) -> Iterable[str]:
        new_path = abspath(other_dir)
        for f in self.files:
            dest = join(new_path, relpath(f, self._parent))
            yield self._link_or_copy_file(f, dest)


def run_cmd(cmd):
    try:
        return check_output(
            cmd,
            stderr=STDOUT,
            universal_newlines=True,
        )
    except CalledProcessError as ex:  # pragma: no cover
        print(debug.format("Error while compiling:\n", ex.output))
        raise


__all__ = [
    "CoconutConfig",
    "ValidationError",
    "discover_root",
    "compile",
    "compiled_files",
]
