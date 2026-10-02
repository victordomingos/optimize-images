#!/usr/bin/env python3
"""Benchmark the SSIM gate: speed per image, global wall time, gate impact.

Meant to be run once per performance commit, always on the same machine,
Python build and corpus, and compared against the previous commit (gain of
that task) and against the baseline (cumulative gain).

Usage:

    # 1. Record a run (in-process per-image timings, read-only on the corpus)
    python benchmarks/ssim_bench.py run --corpus ~/Pictures/bench --label base

    # Optionally add the end-to-end CLI run (works on a temporary copy)
    python benchmarks/ssim_bench.py run --corpus ... --label base --cli

    # 2. Compare two runs (exit code 1 if the gate behaviour changed)
    python benchmarks/ssim_bench.py compare \\
        benchmarks/results/base.json benchmarks/results/float32.json

Per image, the image is optimized in memory through the public API three
ways: without SSIM (``base``), with the gate (``gate``, ``--ssim-min``) and,
with ``--show``, with the score only (``show``). The SSIM cost of an image is
``gate - base``. Each timing is the median of ``--repeat`` runs. The corpus
is only read: nothing is written next to the original files.
"""
import argparse
import json
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimize_images.api import convert_image_data, optimize_image_data  # noqa: E402

EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
DEFAULT_OUT = ROOT / 'benchmarks' / 'results'
SCORE_TOLERANCE = 1e-4


# --------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------

def _environment():
    def version(module):
        try:
            return __import__(module).__version__
        except Exception:
            return None

    def git(*args):
        try:
            return subprocess.run(['git', *args], cwd=ROOT, text=True,
                                  capture_output=True).stdout.strip()
        except OSError:
            return None

    gil = getattr(sys, '_is_gil_enabled', lambda: True)()
    return {
        'date': datetime.now().isoformat(timespec='seconds'),
        'git_commit': git('rev-parse', '--short', 'HEAD'),
        'git_dirty': bool(git('status', '--porcelain', '--', 'optimize_images')),
        'python': platform.python_version(),
        'free_threaded': not gil,
        'platform': platform.platform(),
        'cpu_count': os.cpu_count(),
        'pillow': version('PIL'),
        'numpy': version('numpy'),
        'scikit_image': version('skimage'),
    }


def _images(corpus):
    return sorted(p for p in Path(corpus).rglob('*')
                  if p.is_file() and p.suffix.lower() in EXTENSIONS)


def _timed(func, repeat):
    times = []
    result = None
    for _ in range(max(repeat, 1)):
        start = time.perf_counter()
        result = func()
        times.append(time.perf_counter() - start)
    return statistics.median(times), result


def _measure(path, args):
    data = path.read_bytes()
    if args.convert_to:
        def call(**kw):
            return convert_image_data(data, to=args.convert_to, **kw)
    else:
        def call(**kw):
            return optimize_image_data(data, **kw)

    record = {'file': str(path.relative_to(args.corpus)),
              'orig_size': len(data)}
    modes = {'base': {}, 'gate': {'ssim_min': args.ssim_min}}
    if args.show:
        modes['show'] = {'show_ssim': True}
    for mode, kw in modes.items():
        try:
            seconds, (out, result) = _timed(lambda: call(**kw), args.repeat)
        except Exception as ex:  # keep going; report the failure
            record[mode] = {'error': f'{type(ex).__name__}: {ex}'}
            continue
        record[mode] = {
            'seconds': seconds,
            'was_optimized': result.was_optimized,
            'final_size': len(out),
            'ssim': None if result.ssim is None else float(result.ssim),
            'format': f'{result.orig_format}/{result.orig_mode}',
        }
    return record


_REPORT = re.compile(r'Optimized (\d+) files.*?Total space saved: ([^/\n]+)/',
                     re.S)


def _cli_run(args, extra):
    """Wall time of the real CLI (process/thread pool) on a fresh copy."""
    times, summary = [], None
    for _ in range(args.repeat):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'corpus'
            shutil.copytree(args.corpus, target)
            cmd = [sys.executable, '-m', 'optimize_images', *extra]
            if args.jobs:
                cmd += ['-jobs', str(args.jobs)]
            start = time.perf_counter()
            # cwd=ROOT: run this checkout's code, installed or not.
            proc = subprocess.run([*cmd, str(target)], text=True,
                                  capture_output=True, cwd=ROOT)
            times.append(time.perf_counter() - start)
            match = _REPORT.search(proc.stdout)
            summary = {'returncode': proc.returncode,
                       'optimized': int(match.group(1)) if match else None,
                       'saved': match.group(2).strip() if match else None}
    return {'seconds': statistics.median(times), **(summary or {})}


def cmd_run(args):
    args.corpus = Path(args.corpus).expanduser().resolve()
    images = _images(args.corpus)
    if not images:
        sys.exit(f'No images found in {args.corpus}')

    out_path = Path(args.out) if args.out else DEFAULT_OUT / f'{args.label}.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report = {'label': args.label, 'environment': _environment(),
              'options': {'corpus': str(args.corpus), 'ssim_min': args.ssim_min,
                          'repeat': args.repeat, 'convert_to': args.convert_to,
                          'show': args.show},
              'images': []}

    start = time.perf_counter()
    for i, path in enumerate(images, 1):
        record = _measure(path, args)
        report['images'].append(record)
        cost = _cost(record)
        print(f'[{i}/{len(images)}] {record["file"]}  '
              f'ssim cost {cost:.3f}s' if cost is not None else
              f'[{i}/{len(images)}] {record["file"]}  (error)', flush=True)
    report['in_process_seconds'] = time.perf_counter() - start

    if args.cli:
        gate = ['-ssm', str(args.ssim_min)]
        convert = ['-ca', '-cf', args.convert_to] if args.convert_to else []
        print('CLI run without SSIM...', flush=True)
        report['cli_base'] = _cli_run(args, convert)
        print('CLI run with the gate...', flush=True)
        report['cli_gate'] = _cli_run(args, convert + gate)

    out_path.write_text(json.dumps(report, indent=1))
    print(f'\nSaved {out_path}')


# --------------------------------------------------------------------------
# compare
# --------------------------------------------------------------------------

def _cost(record):
    base, gate = record.get('base', {}), record.get('gate', {})
    if 'seconds' not in base or 'seconds' not in gate:
        return None
    return max(gate['seconds'] - base['seconds'], 0.0)


def _speedup(before, after):
    return before / after if after > 0 else float('inf')


def _human(n):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if abs(n) < 1024:
            return f'{n:.1f} {unit}'
        n /= 1024
    return f'{n:.1f} TB'


def _totals(report, mode):
    rows = [r[mode] for r in report['images'] if 'seconds' in r.get(mode, {})]
    optimized = [r for r in rows if r['was_optimized']]
    saved = sum(img['orig_size'] - img[mode]['final_size']
                for img in report['images']
                if img.get(mode, {}).get('was_optimized'))
    return {'seconds': sum(r['seconds'] for r in rows),
            'optimized': len(optimized), 'saved': saved}


def cmd_compare(args):
    base = json.loads(Path(args.base).read_text())
    new = json.loads(Path(args.new).read_text())
    problems = []

    # Environment: timings are only comparable on the same setup.
    env_keys = ('python', 'free_threaded', 'pillow', 'numpy', 'scikit_image',
                'platform', 'cpu_count')
    for key in env_keys:
        if base['environment'].get(key) != new['environment'].get(key):
            print(f'WARNING: {key} differs: {base["environment"].get(key)} '
                  f'-> {new["environment"].get(key)}')
    if base['options'] != new['options']:
        print(f'WARNING: options differ: {base["options"]} -> {new["options"]}')

    print(f'\n== {base["label"]} ({base["environment"]["git_commit"]}) -> '
          f'{new["label"]} ({new["environment"]["git_commit"]})')

    # Global speed
    print('\nGlobal (in-process, sequential, sum over images):')
    for mode in ('base', 'gate', 'show'):
        if mode not in base['images'][0] or mode not in new['images'][0]:
            continue
        b, n = _totals(base, mode)['seconds'], _totals(new, mode)['seconds']
        print(f'  {mode:5s} {b:9.2f}s -> {n:9.2f}s   x{_speedup(b, n):.2f}')
    old_by_file = {r['file']: r for r in base['images']}
    pairs = [(old_by_file[r['file']], r) for r in new['images']
             if r['file'] in old_by_file]
    b_cost = sum(_cost(o) or 0 for o, _ in pairs)
    n_cost = sum(_cost(n) or 0 for _, n in pairs)
    print(f'  SSIM cost (gate - base) {b_cost:.2f}s -> {n_cost:.2f}s   '
          f'x{_speedup(b_cost, n_cost):.2f}')
    for key in ('cli_base', 'cli_gate'):
        if key in base and key in new:
            b, n = base[key]['seconds'], new[key]['seconds']
            print(f'  CLI {key[4:]:4s} wall {b:7.2f}s -> {n:7.2f}s   '
                  f'x{_speedup(b, n):.2f}   optimized {base[key]["optimized"]}'
                  f' -> {new[key]["optimized"]}, saved {base[key]["saved"]}'
                  f' -> {new[key]["saved"]}')
            if base[key]['optimized'] != new[key]['optimized']:
                problems.append(f'CLI {key}: optimized count changed')

    # Per image speed (largest SSIM cost first)
    print(f'\nPer image (top {args.top} by baseline SSIM cost):')
    print(f'  {"file":40s} {"size":>9s} {"format":10s} {"cost":>8s} '
          f'{"new":>8s} {"speedup":>8s}')
    ranked = sorted(pairs, key=lambda p: _cost(p[0]) or 0, reverse=True)
    for old, cur in ranked[:args.top]:
        oc, nc = _cost(old), _cost(cur)
        if oc is None or nc is None:
            continue
        print(f'  {old["file"][-40:]:40s} {_human(old["orig_size"]):>9s} '
              f'{old["gate"]["format"][:10]:10s} {oc:7.3f}s {nc:7.3f}s '
              f'x{_speedup(oc, nc):7.2f}')

    # Gate impact
    print('\nGate impact:')
    for mode in ('base', 'gate'):
        b, n = _totals(base, mode), _totals(new, mode)
        print(f'  {mode:5s} optimized {b["optimized"]} -> {n["optimized"]}, '
              f'saved {_human(b["saved"])} -> {_human(n["saved"])}')
    changed, sizes, deltas, became_none, errors = [], [], [], [], []
    for old, cur in pairs:
        for mode in ('base', 'gate', 'show'):
            o, c = old.get(mode), cur.get(mode)
            if o is None or c is None:
                continue
            if 'error' in o or 'error' in c:
                if o.get('error') != c.get('error'):
                    errors.append(f'{cur["file"]} [{mode}]: '
                                  f'{o.get("error")} -> {c.get("error")}')
                continue
            if o['was_optimized'] != c['was_optimized']:
                changed.append(f'{cur["file"]} [{mode}]: '
                               f'{o["was_optimized"]} -> {c["was_optimized"]}')
            elif o['final_size'] != c['final_size']:
                sizes.append(f'{cur["file"]} [{mode}]: '
                             f'{o["final_size"]} -> {c["final_size"]}')
            if o['ssim'] is not None and c['ssim'] is not None:
                deltas.append((abs(o['ssim'] - c['ssim']), cur['file'], mode))
            elif o['ssim'] is not None and c['ssim'] is None:
                # Expected only for files the size rule rejected.
                reason = ('size-rejected, expected' if not c['was_optimized']
                          else 'UNEXPECTED')
                became_none.append(f'{cur["file"]} [{mode}] ({reason})')
                if c['was_optimized']:
                    problems.append(f'{cur["file"]}: score lost on a kept file')

    worst = max(deltas, default=(0.0, '-', '-'))
    print(f'  decisions changed: {len(changed)}')
    print(f'  output size changed: {len(sizes)}')
    print(f'  max |score delta|: {worst[0]:.2e} ({worst[1]} [{worst[2]}])')
    print(f'  score no longer computed: {len(became_none)}')
    for label, items in (('Decision changes', changed),
                         ('Output size changes', sizes),
                         ('Score no longer computed', became_none),
                         ('Error changes', errors)):
        for item in items[:args.top]:
            print(f'    {label}: {item}')

    if changed:
        problems.append(f'{len(changed)} gate decision(s) changed')
    if sizes:
        problems.append(f'{len(sizes)} output size(s) changed')
    if worst[0] > args.tolerance:
        problems.append(f'score delta {worst[0]:.2e} > {args.tolerance:g}')
    if errors:
        problems.append(f'{len(errors)} error change(s)')

    print('\nRESULT: ' + ('FAIL - ' + '; '.join(problems) if problems
                         else 'OK - gate behaviour unchanged'))
    return 1 if problems else 0


# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)

    run = sub.add_parser('run', help='measure a corpus and save a JSON report')
    run.add_argument('--corpus', required=True, help='folder of images (read only)')
    run.add_argument('--label', required=True, help='name of this run, e.g. base')
    run.add_argument('--ssim-min', type=float, default=0.98)
    run.add_argument('--repeat', type=int, default=1,
                     help='runs per measurement; the median is kept')
    run.add_argument('--show', action='store_true',
                     help='also time --show-ssim without a threshold')
    run.add_argument('--convert-to', help='benchmark conversion to this format')
    run.add_argument('--cli', action='store_true',
                     help='also time the real CLI on a temporary copy')
    run.add_argument('--jobs', type=int, default=0, help='CLI -jobs value')
    run.add_argument('--out', help='output JSON (default benchmarks/results/<label>.json)')
    run.set_defaults(func=cmd_run)

    cmp_ = sub.add_parser('compare', help='compare two JSON reports')
    cmp_.add_argument('base')
    cmp_.add_argument('new')
    cmp_.add_argument('--top', type=int, default=10)
    cmp_.add_argument('--tolerance', type=float, default=SCORE_TOLERANCE)
    cmp_.set_defaults(func=cmd_compare)

    args = parser.parse_args()
    sys.exit(args.func(args) or 0)


if __name__ == '__main__':
    main()
