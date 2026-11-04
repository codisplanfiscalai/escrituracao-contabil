"""GitHub REST por gh autenticado; não imprime tokens."""
import json
import os
import re
import subprocess


def repository():
    value = os.environ.get('GITHUB_REPOSITORY') or subprocess.check_output(['gh', 'repo', 'view', '--json', 'nameWithOwner', '--jq', '.nameWithOwner'], text=True).strip()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', value):
        raise ValueError('Repositório inválido.')
    return value


def api(path, method='GET', payload=None):
    command = ['gh', 'api', '--method', method, path]
    if payload is not None: command += ['--input', '-']
    result = subprocess.run(command, input=json.dumps(payload) if payload is not None else None, text=True, capture_output=True)
    if result.returncode:
        if 'HTTP 404' in result.stderr: return None
        raise RuntimeError(f'GitHub recusou {method} {path}: {result.stderr.strip()}')
    return json.loads(result.stdout) if result.stdout.strip() else {}


def pages(path, field=None):
    page = 1
    while True:
        separator = '&' if '?' in path else '?'
        value = api(f'{path}{separator}per_page=100&page={page}')
        if value is None: raise RuntimeError('Recurso ausente ou inacessível.')
        rows = value[field] if field else value
        yield from rows
        if len(rows) < 100: break
        page += 1
