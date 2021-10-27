import os
import stat
import sys
import traceback
import warnings
from pathlib import Path
from shutil import rmtree
from time import sleep
from typing import List
from zipfile import ZipFile

from setuptools import build_meta as setuptools

from setuptools_coconut.api import run_cmd


def rmpath(path):
    try:
        rmtree(str(path), onerror=set_writable)
    except FileNotFoundError:
        return
    except Exception:
        msg = f"Error when trying to remove {path!r}\n\n"
        warnings.warn(msg + traceback.format_exc())


def set_writable(func, path, _exc_info):
    sleep(1)

    if not Path(path).exists():
        return  # we just want to remove files anyway

    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR)

    # now it either works or re-raise the exception
    func(path)


def list_zip(p: Path) -> List[str]:
    with ZipFile(str(p), "r") as zipfile:
        return zipfile.namelist()


def build_wheel():
    """Build a wheel for the project in the CWD"""
    print(f"Current directory: {os.getcwd()}")
    if Path("setup.py").exists() and not Path("pyproject.toml").exists():
        run_cmd([sys.executable, "setup.py", "bdist_wheel"])
    else:
        setuptools.build_wheel("dist")
