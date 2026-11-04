"""Versionamento SemVer do Escritura. Não cria tags nem altera branches."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
STABLE = re.compile(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)')
BUILD = re.compile(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-dev\.([1-9][0-9]*)\.([1-9][0-9]*))?')


def parse(value):
    match = STABLE.fullmatch(value)
    if not match:
        raise ValueError('Use MAJOR.MINOR.PATCH, sem prefixo e sem zeros à esquerda.')
    return tuple(map(int, match.groups()))


def bump(value, kind):
    major, minor, patch = parse(value)
    if kind == 'major': return f'{major+1}.0.0'
    if kind == 'minor': return f'{major}.{minor+1}.0'
    if kind == 'patch': return f'{major}.{minor}.{patch+1}'
    raise ValueError('Incremento deve ser patch, minor ou major.')


def read_version(root=ROOT):
    version = (root / 'VERSION').read_text(encoding='utf-8').strip()
    parse(version)
    match = re.search(r'^version = "([^"]+)"$', (root / 'pyproject.toml').read_text(encoding='utf-8'), re.M)
    if not match or match[1] != version:
        raise ValueError('VERSION e pyproject.toml devem coincidir.')
    return version


def set_version(version, root=ROOT):
    parse(version)
    project = root / 'pyproject.toml'
    text, count = re.subn(r'^version = "[^"]+"$', f'version = "{version}"', project.read_text(encoding='utf-8'), flags=re.M)
    if count != 1:
        raise ValueError('Esperado exatamente um campo version em pyproject.toml.')
    project.write_text(text, encoding='utf-8')
    (root / 'VERSION').write_text(version + '\n', encoding='utf-8')


def build_version(base, channel, run='1', attempt='1'):
    parse(base)
    if channel == 'stable': return base
    if channel != 'develop' or not all(re.fullmatch(r'[1-9][0-9]*', str(v)) for v in (run, attempt)):
        raise ValueError('Canal ou execução inválida.')
    return f'{base}-dev.{run}.{attempt}'


def validate_build(value, base):
    if not BUILD.fullmatch(value) or value.split('-')[0] != base:
        raise ValueError('Versão do build deve pertencer à versão base de VERSION.')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('check')
    change = sub.add_parser('set')
    change.add_argument('version')
    change = sub.add_parser('bump')
    change.add_argument('kind', choices=['patch', 'minor', 'major'])
    resolve = sub.add_parser('resolve')
    resolve.add_argument('--channel', required=True, choices=['develop', 'stable'])
    args = parser.parse_args()
    if args.command == 'set': set_version(args.version)
    elif args.command == 'bump': set_version(bump(read_version(), args.kind))
    version = read_version()
    result = {'base_version': version}
    if args.command == 'resolve':
        sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        result.update(version=build_version(version, args.channel, os.getenv('GITHUB_RUN_NUMBER', '1'), os.getenv('GITHUB_RUN_ATTEMPT', '1')), source_sha=sha, channel=args.channel)
        result['tag'] = result['version']
    print(json.dumps(result, indent=2))
    if os.getenv('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as handle:
            handle.writelines(f'{key}={value}\n' for key, value in result.items())


if __name__ == '__main__': main()
