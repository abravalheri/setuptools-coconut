import os
import sys
from functools import lru_cache
from glob import glob
from os.path import abspath, dirname, exists, join, relpath
from subprocess import STDOUT, CalledProcessError, check_output
from typing import Iterable, Optional

from . import debug
from .config import DEFAULT_CONFIG_FILE, CoconutConfig, ValidationError

EXECUTABLE = (sys.executable, "-m", "coconut")
PROJECT_MARKERS = ("pyproject.toml", "setup.cfg", ".git", ".hg")


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
        try:
            check_output(
                [*EXECUTABLE, src_root, dest_root, *opts],
                stderr=STDOUT,
                universal_newlines=True,
            )
        except CalledProcessError as ex:
            print(debug.format("Error while compiling:\n", ex.output))
            raise
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

    abs_path = abspath(path or ".").rstrip(os.pathsep).replace(os.pathsep, "/")
    debug.print(f"Parent directory (from setuptools integration): {abs_path}")
    for compiled_path in compile(root, config):
        if compiled_path.replace(os.pathsep, "/").startswith(abs_path):
            for file in glob(join(compiled_path, "**", "*.py")):
                yield debug.inspect(relpath(file, abs_path))
        else:
            compiled_relpath = relpath(compiled_path, path)
            debug.print(f"{compiled_relpath!r} should be inside {path!r}")


__all__ = [
    "CoconutConfig",
    "ValidationError",
    "discover_root",
    "compile",
    "compiled_files",
]
