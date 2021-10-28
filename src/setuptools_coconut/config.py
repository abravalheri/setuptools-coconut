import os
from os.path import exists, join
from typing import Dict, List, Optional, Tuple, Type, TypeVar, Union

import pydantic
import tomli

from . import debug

T = TypeVar("T", bound="CoconutConfig")
PathLike = Union[str, os.PathLike]

DEFAULT_CONFIG_FILE = "pyproject.toml"
TOOL_NAME = "coconut"


class CoconutConfig(pydantic.BaseModel, frozen=True, extra=pydantic.Extra.forbid):
    """Options that will be passed to the ``coconut`` compiler.

    For more information, please check `coconut docs
    <https://coconut.readthedocs.io/en/master/DOCS.html#compilation>`_
    """

    src: Tuple[str, ...] = ("src",)
    """Folders containing ``.coco`` files to compile."""

    dest: Optional[str] = None
    """Folder where the generated files will be placed.
    If ``dest`` is not set, compiled files will live along side coconut files.
    If ``dest`` is passed, each ``src`` folder will have a correspondent inside
    of it:

    For example, if your configuration is:

    .. code-block:: toml

       src = ["src"]
       dest = None   # default

    then a ``src/module.coco`` file would be compiled into ``src/moldule.py``.
    One the other hand, if your configuration is:

    .. code-block:: toml

       src = ["src"]
       dest = "build"

    then a ``src/module.coco`` file would be compiled into ``build/src/moldule.py``.
    """

    strict: bool = True
    """Instruct coconut to perform additional checks in your code. It helps to
    improve code quality.
    """

    target: str = "3.6"
    """Which version of Python the code will be compiled into.

    You probably want to check the `active Python releases
    <https://www.python.org/downloads/>`_ table and choose the one with the
    earliest **end-of-life** date that is still supported.
    """

    tco: bool = True
    """Compile the code with `tail call optimisation
    <https://coconut.readthedocs.io/en/master/DOCS.html#tail-call-optimization>`_.

    TCO-compiled code might run slightly slower due to some overhead, but it
    can make developer's life easier...
    """

    wrap: bool = True
    """Type hints are wrapped in strings"""

    mypy: bool = False
    """Type check the generated code with ``mypy``.

    To configure typecheck options, please use `mypy configuration files
    <https://mypy.readthedocs.io/en/stable/config_file.html>`_
    """

    processes: Union[int, str] = "sys"
    """Number of processes to use. When ``"sys"`` is passed, ``coconut`` will
    try to automatically detect the number of cores in the machine.
    """

    argv: Tuple[str, ...] = ()
    """Extra arguments passed directly to the ``coconut`` compilation script"""

    @pydantic.validator("dest")
    def dest_cannot_be_src(cls, v, values, **kwargs):
        if any(v == src for src in values["src"]):
            msg = "To avoid recursion `dest` cannot be the same as `src`. Given:\n"
            msg += f"src = {list(values['src'])!r}\ndest = {v!r}"
            raise ValueError("To avoid recursion `dest` cannot be the same as `src`")
        return v

    def as_cli_args(self) -> List[str]:
        args = ["--target", self.target, "-j", str(self.processes)]
        flags = {
            "--no-tco": self.tco is False,
            "--no-wrap": self.wrap is False,
            "--strict": self.strict,
            "--mypy": self.mypy,
        }
        args.extend(k for k, v in flags.items() if v)
        if self.argv:
            args.extend(self.argv)
        return args

    def build_paths(self) -> Dict[str, str]:
        if self.dest is None:
            return {s: s for s in self.src}
        return {s: join(self.dest, s) for s in self.src}

    @classmethod
    def from_file(cls: Type[T], file: PathLike) -> Optional[T]:
        """Reads the configuration from a file in the same format as ``pyproject.toml``
        (:pep:`518`).

        The configurations for the ``coconut`` compiler should be stored in the
        ``tool.coconut`` table.
        """
        coconut_config = None
        if file and exists(file):
            with open(file, "rb") as f:
                config = tomli.load(f)
            coconut_config = config.get("tool", {}).get(TOOL_NAME, None)
        else:
            debug.print(f"No configuration file: `{file}`")
            return None

        if coconut_config is None:
            debug.print(f"No table [tool.{TOOL_NAME}] found in `{file!r}`")
            return None

        try:
            return cls(**coconut_config)
        except pydantic.ValidationError as ex:
            raise ValidationError(file, ex)


class ValidationError(pydantic.ValidationError):
    __slots__ = ("file", "__cause__")

    def __init__(self, file: PathLike, cause: pydantic.ValidationError):
        super().__init__(cause.raw_errors, cause.model)
        self.file = file
        self.__cause__ = cause

    def __str__(self):
        msg = debug.format(f"Invalid configuration file {self.file}\n")
        return msg + super().__str__()


__all__ = ["CoconutConfig", "ValidationError"]
