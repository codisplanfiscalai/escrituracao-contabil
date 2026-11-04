"""Limpeza limitada a caches do Escritura; simulação por padrão."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
from github_api import api, pages, repository

ROOT = Path(__file__).resolve().parents[2]


def select_caches(caches, now, days, pr_number=None):
    if days < 1: raise ValueError('Retenção mínima: um dia.')
    if pr_number is not None and not re.fullmatch(r'[1-9][0-9]*', str(pr_number)):
        raise ValueError('PR inválida.')
    rows = [row for row in caches if row.get('key', '').startswith('escritura-')]
    if pr_number:
        refs = {f'refs/pull/{pr_number}/merge', f'refs/pull/{pr_number}/head'}
        return [row for row in rows if row.get('ref') in refs]
    newest = {}
    for row in rows:
        key = (row.get('ref'), row.get('key', '').split('-deps-')[0])
        if key not in newest or row['last_accessed_at'] > newest[key]['last_accessed_at']: newest[key] = row
    keep = {row['id'] for row in newest.values()}
    threshold = now - timedelta(days=days)
    return [row for row in rows if row['id'] not in keep and datetime.fromisoformat(row['last_accessed_at'].replace('Z', '+00:00')) < threshold]


def local_candidates(root=ROOT):
    result = [root / name for name in ('build', 'dist', 'artifacts', '.pytest_cache', '.mypy_cache', '.ruff_cache')]
    for area in ('src', 'tests', 'packaging', 'scripts'):
        result += list((root / area).rglob('__pycache__'))
    safe = []
    tracked = set(subprocess.check_output(['git', 'ls-files'], cwd=root, text=True).splitlines())
    for path in result:
        if not path.exists() and not path.is_symlink(): continue
        if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != root.parent):
            raise ValueError('Limpeza recusada: link simbólico no caminho.')
        relative = path.relative_to(root).as_posix()
        if root.resolve() not in path.resolve().parents: raise ValueError('Destino fora do projeto.')
        if any(item == relative or item.startswith(relative + '/') for item in tracked):
            raise ValueError('Limpeza recusada: destino contém arquivo versionado.')
        safe.append(path)
    return safe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scope', choices=['local', 'cache'])
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--days', type=int, default=14)
    parser.add_argument('--pr-number', type=int)
    args = parser.parse_args()
    if args.scope == 'local':
        paths = local_candidates()
        print(json.dumps({'apply': args.apply, 'paths': [str(p.relative_to(ROOT)) for p in paths]}, indent=2))
        if args.apply:
            for path in paths:
                if path.is_dir(): shutil.rmtree(path)
                else: path.unlink()
        return
    repo = repository()
    if args.pr_number:
        pr = api(f'repos/{repo}/pulls/{args.pr_number}')
        if not pr or pr['state'] != 'closed': raise ValueError('Somente caches de PR encerrada podem ser removidos por este modo.')
    rows = list(pages(f'repos/{repo}/actions/caches', 'actions_caches'))
    candidates = select_caches(rows, datetime.now(timezone.utc), args.days, args.pr_number)
    print(json.dumps({'apply': args.apply, 'caches': [{k: r[k] for k in ('id', 'key', 'ref', 'last_accessed_at')} for r in candidates]}, indent=2))
    if args.apply:
        for row in candidates:
            api(f'repos/{repo}/actions/caches/{int(row["id"])}', 'DELETE')


if __name__ == '__main__': main()
