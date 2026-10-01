"""Helpers shared by the tests that run the command-line interface.

The CLI is started as ``python -m optimize_images`` with the interpreter that
runs pytest and the repository root as working directory, so the tests use
the code in this checkout and the dependencies of the active venv, whether or
not the package is installed there.
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEST_IMAGES = Path(__file__).resolve().parent / "test-images"


def cli_command(*args):
    return [sys.executable, "-m", "optimize_images", *map(str, args)]


def run_cli(*args, **kwargs):
    """Run the CLI to completion and return the CompletedProcess."""
    kwargs.setdefault("capture_output", True)
    kwargs.setdefault("text", True)
    kwargs.setdefault("timeout", 120)
    return subprocess.run(cli_command(*args), cwd=REPO_ROOT, **kwargs)


def start_cli(*args, **kwargs):
    """Start the CLI in the background (e.g. watch mode) and return the Popen."""
    kwargs.setdefault("stdout", subprocess.PIPE)
    kwargs.setdefault("stderr", subprocess.PIPE)
    kwargs.setdefault("text", True)
    return subprocess.Popen(cli_command(*args), cwd=REPO_ROOT, **kwargs)
