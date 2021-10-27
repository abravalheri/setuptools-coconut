import os
import sys

from . import dist_name

DEBUG = os.getenv("SETUPTOOLS_COCONUT_DEBUG") not in (None, "false", "0")
LABEL = f"[{dist_name}]"
INDENT = " " * (len(LABEL) + 1)

print_function = print


def format(*args):
    text = LABEL + " " + " ".join(str(x) for x in args)
    lines = text.splitlines(keepends=True)
    lines = [lines[0], *(INDENT + x for x in lines[1:])]
    return "".join(lines)


def print(*args):
    if DEBUG:
        print_function(format(*args), flush=True, file=sys.stderr)


def inspect(arg):
    print(arg)
    return arg


def lazy(fn, *args, **kwargs):
    if DEBUG:
        print(fn(*args, **kwargs))
