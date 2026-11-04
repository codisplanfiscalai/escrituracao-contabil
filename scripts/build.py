"""Entrada única de verificações e builds locais/CI, sem publicar."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts' / 'ci'))
from version import read_version, validate_build


def run(*args, **kwargs):
    print('+', ' '.join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), cwd=ROOT, check=True, **kwargs)


def check():
    read_version()
    run(sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v')
    run(sys.executable, '-m', 'unittest', 'discover', '-s', 'packaging', '-p', 'test_*.py', '-v')
    run(sys.executable, '-m', 'unittest', 'discover', '-s', 'scripts/ci/tests', '-v')
    run(sys.executable, '-m', 'compileall', '-q', 'src', 'tests', 'packaging', 'scripts')
    for file in sorted((ROOT / 'src/web').glob('*.js')):
        run('node', '--check', file)
    run('node', 'tests/test_posting_math.cjs')
    run(sys.executable, 'packaging/verify_icons.py')
    run(sys.executable, 'packaging/smoke_test.py')


def windows(arch, version, install):
    if sys.platform != 'win32':
        raise ValueError('Windows exige execução nativa. Use os jobs x86/x64 da CI.')
    if install:
        run(sys.executable, '-m', 'pip', 'install', '--only-binary=:all:', '--require-hashes', '-r', 'packaging/requirements-build.txt')
    npm = shutil.which('npm')
    if not npm: raise ValueError('Node/npm não encontrado.')
    run(npm, 'ci', '--prefix', 'packaging/icon-tools', '--ignore-scripts', '--no-audit', '--no-fund')
    run('node', 'packaging/icon-tools/generate.mjs', '--check')
    check()
    run(sys.executable, 'packaging/build_windows.py', '--arch', arch, '--version', version)


def container(version, no_cache):
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if not re.fullmatch(r'[0-9a-f]{40}', sha): raise ValueError('SHA inválido.')
    image = f'escritura-build:{version}'
    cache = ['--no-cache'] if no_cache else []
    run('docker', 'build', *cache, '--target', 'test', '--tag', 'escritura-tests:local', '.')
    run('docker', 'build', *cache, '--target', 'final', '--label', f'org.opencontainers.image.version={version}', '--label', f'org.opencontainers.image.revision={sha}', '--tag', image, '.')
    run('docker', 'run', '--rm', '--network', 'none', '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--tmpfs', '/tmp:rw,nosuid,nodev,mode=1777', '--tmpfs', '/data:rw,nosuid,nodev,uid=10001,gid=10001,mode=0700', '--entrypoint', 'python', image, 'packaging/smoke_test.py')
    image_id = subprocess.check_output(['docker', 'image', 'inspect', '--format', '{{.Id}}', image], text=True).strip()
    out = ROOT / 'artifacts'; out.mkdir(exist_ok=True)
    tar = out / 'container.tar'
    run('docker', 'save', '--output', tar, image)
    archive = out / 'container.tar.gz'
    with tar.open('rb') as source, archive.open('wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as target:
        shutil.copyfileobj(source, target)
    tar.unlink()
    hasher = hashlib.sha256()
    with archive.open('rb') as handle:
        for block in iter(lambda: handle.read(1024*1024), b''): hasher.update(block)
    manifest = {'schema': 1, 'version': version, 'source_sha': sha, 'image': image, 'image_id': image_id, 'file': archive.name, 'sha256': hasher.hexdigest(), 'size': archive.stat().st_size, 'smoke_test': 'passed'}
    (out / 'container.manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', choices=['check', 'windows', 'container', 'all'])
    parser.add_argument('--arch', choices=['x86', 'x64'], default='x64')
    parser.add_argument('--version')
    parser.add_argument('--install-build-tools', action='store_true')
    parser.add_argument('--no-cache', action='store_true')
    args = parser.parse_args()
    version = validate_build(args.version or read_version(), read_version())
    if args.target == 'check': check()
    elif args.target == 'windows': windows(args.arch, version, args.install_build_tools)
    elif args.target == 'container': container(version, args.no_cache)
    else:
        if sys.platform == 'win32': windows(args.arch, version, args.install_build_tools)
        else: check()
        container(version, args.no_cache)


if __name__ == '__main__': main()
