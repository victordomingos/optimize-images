#!/usr/bin/env python3
"""Run the test suite in every local multi-Python venv and print a matrix.

The venvs live at the repository root and are named after the Python version:
venv311, venv312, venv313, venv313t, ... ("t" = free-threaded build). They
are gitignored. Each one runs ``python -m pytest`` from the repository root,
so pytest.ini applies and no editable install is needed.

Examples (from the repository root):

    python scripts/test_matrix.py                 # all existing venvs
    python scripts/test_matrix.py --create        # also create missing venvs
    python scripts/test_matrix.py --install       # update requirements first
    python scripts/test_matrix.py --only 3.14t,3.13 --fast
    python scripts/test_matrix.py -- -k watch     # extra pytest arguments

Standard library only.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
PYTEST_TIMEOUT = 30 * 60  # seconds; a normal run takes about one minute
VERSIONS = ["3.11", "3.12", "3.13", "3.13t", "3.14", "3.14t", "3.15", "3.15t"]
DEV_REQUIREMENTS = REPO_ROOT / "requirements-dev.txt"
RUNTIME_REQUIREMENTS = REPO_ROOT / "requirements.txt"

PROBE = (
    "import importlib.util, json, sys, sysconfig\n"
    "print(json.dumps({\n"
    "    'version': sys.version.split()[0],\n"
    "    'free_threaded': bool(sysconfig.get_config_var('Py_GIL_DISABLED')),\n"
    "    'skimage': importlib.util.find_spec('skimage') is not None,\n"
    "    'yaml': importlib.util.find_spec('yaml') is not None,\n"
    "    'pytest': importlib.util.find_spec('pytest') is not None,\n"
    "}))\n"
)


@dataclass
class Result:
    version: str
    venv: Path
    status: str = "ok"            # ok | missing | broken | failed
    python: str = ""
    free_threaded: Optional[bool] = None
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    xfailed: int = 0
    seconds: float = 0.0
    notes: List[str] = field(default_factory=list)
    failures: List[str] = field(default_factory=list)
    log: Optional[Path] = None


def venv_dir(version: str) -> Path:
    return REPO_ROOT / ("venv" + version.replace(".", ""))


def venv_python(venv: Path) -> Path:
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def run(cmd, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run([str(c) for c in cmd], cwd=REPO_ROOT,
                          capture_output=True, text=True, **kwargs)


# --- venv creation -------------------------------------------------------

def dev_requirement_lines() -> List[str]:
    lines = []
    for line in DEV_REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line and not line.startswith("-r"):
            lines.append(line)
    return lines


def create_venv(version: str, recreate: bool) -> Optional[List[str]]:
    """Create venvXXX with python<version> and install the requirements.

    Returns the install notes, or None when the venv already existed.
    """
    venv = venv_dir(version)
    if venv.exists() and not recreate:
        return None
    if venv.exists() and Path(sys.prefix).resolve() == venv.resolve():
        raise RuntimeError("cannot recreate the venv running this script")
    interpreter = shutil.which(f"python{version}")
    if interpreter is None:
        raise RuntimeError(f"interpreter python{version} not found on PATH")
    if venv.exists():
        shutil.rmtree(venv)
    proc = run([interpreter, "-m", "venv", venv])
    if proc.returncode:
        raise RuntimeError(f"venv creation failed: {proc.stderr.strip()}")

    return install_requirements(venv)


def install_requirements(venv: Path) -> List[str]:
    """Install requirements.txt, then each dev requirement on its own, so one
    package without a wheel for this Python (e.g. on a new release) does not
    leave the venv unusable; failures are returned as notes."""
    python = venv_python(venv)
    run([python, "-m", "pip", "install", "-q", "--upgrade", "pip"])
    pip = [python, "-m", "pip", "install", "-q", "--prefer-binary"]
    proc = run(pip + ["-r", RUNTIME_REQUIREMENTS])
    if proc.returncode:
        raise RuntimeError("runtime requirements failed: "
                           + proc.stderr.strip().splitlines()[-1])
    notes = []
    for requirement in dev_requirement_lines():
        proc = run(pip + [requirement])
        if proc.returncode:
            notes.append(f"could not install {requirement}")
    return notes


# --- running -------------------------------------------------------------

def probe(python: Path) -> dict:
    import json
    proc = run([python, "-c", PROBE], timeout=60)
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip().splitlines()[-1]
                           if proc.stderr.strip() else "probe failed")
    return json.loads(proc.stdout)


def parse_junit(path: Path, result: Result) -> None:
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
    # Collection errors are reported as testcases with an <error> element.
    for suite in suites:
        for case in suite.iter("testcase"):
            name = f"{case.get('classname', '')}::{case.get('name', '')}"
            if case.find("failure") is not None:
                result.failed += 1
                result.failures.append(name)
            elif case.find("error") is not None:
                result.errors += 1
                result.failures.append(name + " (error)")
            elif (skipped := case.find("skipped")) is not None:
                if skipped.get("type") == "pytest.xfail":
                    result.xfailed += 1
                else:
                    result.skipped += 1
            else:
                result.passed += 1


def run_venv(version: str, args, log_dir: Path) -> Result:
    venv = venv_dir(version)
    result = Result(version, venv)
    python = venv_python(venv)

    created = None
    if args.create or args.recreate:
        try:
            created = create_venv(version, args.recreate)
        except (RuntimeError, OSError) as exc:
            result.status = "missing"
            result.notes.append(str(exc))
            return result
        result.notes += created or []
    if args.install and created is None and python.exists():
        try:
            result.notes += install_requirements(venv)
        except (RuntimeError, OSError) as exc:
            result.status = "broken"
            result.notes.append(str(exc))
            return result
    if not python.exists():
        result.status = "missing"
        result.notes.append("venv not found (use --create)")
        return result

    try:
        info = probe(python)
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        result.status = "broken"
        result.notes.append(f"interpreter does not start: {exc}")
        return result
    result.python = info["version"]
    result.free_threaded = info["free_threaded"]
    if version.endswith("t") != info["free_threaded"]:
        result.status = "broken"
        result.notes.append("wrong build: free-threading does not match the "
                            "venv name")
        return result
    if not info["pytest"]:
        result.status = "broken"
        result.notes.append("pytest is not installed")
        return result
    if not info["skimage"]:
        result.notes = [n for n in result.notes if "scikit-image" not in n]
        result.notes.append("no scikit-image: SSIM tests skipped")
    if not info["yaml"]:
        result.notes = [n for n in result.notes if "pyyaml" not in n.lower()]
        result.notes.append("no PyYAML: CLI/watch case tests skipped")

    junit = log_dir / f"{venv.name}.xml"
    result.log = log_dir / f"{venv.name}.log"
    cmd = [python, "-m", "pytest", "-q", "-p", "no:cacheprovider",
           f"--junitxml={junit}"]
    if args.fast:
        cmd += ["-m", "not slow"]
    cmd += args.pytest_args
    start = time.monotonic()
    try:
        proc = run(cmd, timeout=PYTEST_TIMEOUT)
    except subprocess.TimeoutExpired as exc:
        result.seconds = time.monotonic() - start
        output = (exc.stdout or "") + (exc.stderr or "")
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
        result.log.write_text(output, encoding="utf-8")
        result.status = "failed"
        result.notes.append(f"timed out after {PYTEST_TIMEOUT} s")
        return result
    result.seconds = time.monotonic() - start
    result.log.write_text(proc.stdout + proc.stderr, encoding="utf-8")

    if junit.exists():
        parse_junit(junit, result)
    else:
        result.status = "failed"
        result.notes.append(f"pytest exited with {proc.returncode}, "
                            "no report written (see log)")
        return result
    if proc.returncode not in (0, 5) or result.failed or result.errors:
        result.status = "failed"
    return result


# --- report --------------------------------------------------------------

def print_report(results: List[Result], log_dir: Path) -> None:
    headers = ["venv", "Python", "GIL", "passed", "failed", "errors",
               "skipped", "xfailed", "time", "status / notes"]
    rows = []
    for r in results:
        gil = "" if r.free_threaded is None else (
            "off" if r.free_threaded else "on")
        counted = r.status in ("ok", "failed") and r.log is not None
        nums = [str(n) if counted else "" for n in
                (r.passed, r.failed, r.errors, r.skipped, r.xfailed)]
        time_text = f"{r.seconds:.0f}s" if counted else ""
        notes = "; ".join([r.status] + r.notes)
        rows.append([r.venv.name, r.python, gil, *nums, time_text, notes])
    widths = [max(len(h), *(len(row[i]) for row in rows))
              for i, h in enumerate(headers)]
    line = "  ".join(h.ljust(w) for h, w in zip(headers, widths))
    print("\n" + line.rstrip() + "\n" + "-" * len(line.rstrip()))
    for row in rows:
        print("  ".join(c.ljust(w) for c, w in zip(row, widths)).rstrip())

    for r in results:
        if r.failures:
            print(f"\n{r.venv.name} failures:")
            for name in r.failures:
                print(f"  - {name}")
    print(f"\nLogs and JUnit reports: {log_dir}")


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    pytest_args = []
    if "--" in argv:
        index = argv.index("--")
        argv, pytest_args = argv[:index], argv[index + 1:]

    parser = argparse.ArgumentParser(
        description="Run the test suite in every local multi-Python venv "
                    "and print a matrix.",
        epilog="Arguments after -- are passed to pytest.")
    parser.add_argument("--only", help="comma-separated versions, e.g. "
                        "3.14t,3.13 (default: all of "
                        + ", ".join(VERSIONS) + ")")
    parser.add_argument("--create", action="store_true",
                        help="create missing venvs with python<version> from "
                             "PATH (e.g. python3.13t) and install the dev "
                             "requirements; on Windows create them by hand "
                             "with the py launcher")
    parser.add_argument("--recreate", action="store_true",
                        help="delete and recreate the selected venvs (e.g. "
                             "after a new Python release)")
    parser.add_argument("--install", action="store_true",
                        help="install or update the requirements in the "
                             "existing venvs before testing")
    parser.add_argument("--fast", action="store_true",
                        help='skip tests marked slow (-m "not slow")')
    default_jobs = max(1, (os.cpu_count() or 4) // 4)
    parser.add_argument("--jobs", type=int, default=default_jobs,
                        help=f"venvs tested at the same time (default "
                             f"{default_jobs}; 1 = one after another)")
    parser.add_argument("--strict", action="store_true",
                        help="treat missing venvs as a failure")
    args = parser.parse_args(argv)
    args.pytest_args = pytest_args

    versions = VERSIONS
    if args.only:
        versions = [v.strip() for v in args.only.split(",") if v.strip()]
        unknown = [v for v in versions if v not in VERSIONS]
        if unknown:
            parser.error(f"unknown version(s): {', '.join(unknown)}; "
                         f"choose from {', '.join(VERSIONS)}")

    log_dir = Path(tempfile.mkdtemp(prefix="test-matrix-"))
    jobs = max(1, min(args.jobs, len(versions)))
    print(f"Testing {', '.join(versions)} ({jobs} at a time)...")
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        results = list(pool.map(lambda v: run_venv(v, args, log_dir),
                                versions))
    print_report(results, log_dir)

    bad = {"failed", "broken"} | ({"missing"} if args.strict else set())
    return 1 if any(r.status in bad for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
