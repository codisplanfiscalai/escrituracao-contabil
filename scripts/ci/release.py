"""Publica os mesmos bytes testados; não recompila nem substitui versões estáveis."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import quote

from github_api import api, pages, repository
from version import parse, validate_build, read_version

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'packaging'))
from verify_artifacts import verify
from check_ghcr_visibility import check


def run(*args, **kwargs):
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def digest(path):
    hasher = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024*1024), b''): hasher.update(block)
    return hasher.hexdigest()


def verify_container(folder, sha, version):
    meta = json.loads((folder / 'container.manifest.json').read_text(encoding='utf-8'))
    if meta['source_sha'] != sha or meta['version'] != version or meta['smoke_test'] != 'passed':
        raise ValueError('Contêiner não pertence à revisão/versão testada.')
    if meta['file'] != 'container.tar.gz' or meta['image'] != f'escritura-build:{version}': raise ValueError('Nome de artefato inválido.')
    file = folder / meta['file']
    if digest(file) != meta['sha256'] or file.stat().st_size != meta['size']: raise ValueError('Contêiner corrompido.')
    if not re.fullmatch(r'sha256:[a-f0-9]{64}', meta['image_id']): raise ValueError('Image ID inválido.')
    return meta


def verify_release_files(folder, manifest, sha, version):
    if manifest['source_sha'] != sha or manifest['version'] != version: raise ValueError('Release já existe para outra revisão.')
    for item in manifest['files']:
        name = item['name']
        if Path(name).name != name or '/' in name or '\\' in name: raise ValueError('Caminho inválido no manifesto.')
        path = folder / name
        if path.stat().st_size != item['size'] or digest(path) != item['sha256']: raise ValueError(f'Artefato divergente: {name}')


def existing_release(repo, tag, sha, folder):
    release = api(f'repos/{repo}/releases/tags/{quote(tag, safe="")}')
    if not release or release.get('draft'): return release, False
    with tempfile.TemporaryDirectory() as temporary:
        run('gh', 'release', 'download', tag, '--repo', repo, '--dir', temporary)
        root = Path(temporary)
        manifest = json.loads((root / 'release.json').read_text(encoding='utf-8'))
        verify_release_files(root, manifest, sha, tag)
        verify(root, sha)
        verify_container(root, sha, tag)
    print('Release existente conferida; nenhum artefato ou alias foi alterado.')
    return release, True


def publish(folder, version, sha, channel, owner_type):
    if not re.fullmatch(r'[a-f0-9]{40}', sha): raise ValueError('SHA inválido.')
    validate_build(version, read_version())
    if (channel == 'stable') != ('-dev.' not in version): raise ValueError('Versão incompatível com canal.')
    repo = repository()
    info = api(f'repos/{repo}')
    if not info or info.get('archived'): raise ValueError('Repositório indisponível ou arquivado.')
    branch = 'main' if channel == 'stable' else 'develop'
    ref = api(f'repos/{repo}/git/ref/heads/{branch}')
    # O commit precisa estar contido na branch autorizada; nunca aceitar um SHA externo.
    comparison = api(f'repos/{repo}/compare/{sha}...{ref["object"]["sha"]}')
    if not comparison or comparison['status'] not in ('ahead', 'identical'):
        raise ValueError('Revisão não pertence à branch de publicação.')
    current, complete = existing_release(repo, version, sha, folder)
    if complete: return
    tag = api(f'repos/{repo}/git/ref/tags/{quote(version, safe="")}')
    if tag and (tag['object']['type'] != 'commit' or tag['object']['sha'] != sha):
        raise ValueError('Tag existente é imutável e aponta para outra revisão/tipo.')
    verify(folder, sha)
    for path in folder.glob('*.manifest.json'):
        if path.name == 'container.manifest.json': continue
        if json.loads(path.read_text(encoding='utf-8'))['version'] != version: raise ValueError('Windows com versão divergente.')
    container = verify_container(folder, sha, version)
    run('docker', 'load', '--input', folder / container['file'])
    local = json.loads(subprocess.check_output(['docker', 'image', 'inspect', container['image']], text=True))[0]
    labels = local['Config'].get('Labels', {})
    if local['Id'] != container['image_id'] or labels.get('org.opencontainers.image.revision') != sha or labels.get('org.opencontainers.image.version') != version:
        raise ValueError('Imagem carregada não corresponde ao manifesto.')
    image = f'ghcr.io/{repo.lower()}'
    remote = f'{image}:{version}'
    # Repositório público admite pacote público ou privado; privado exige privado.
    allowed_visibility = ('private', 'public') if info.get('private') is False else ('private',)
    before_visibility = check(repo, owner_type, os.environ['GH_TOKEN'], allow_missing=True,
                              allowed_visibilities=allowed_visibility)
    # Consulta tags do pacote; falha de autorização não equivale a versão ausente.
    owner, package_name = repo.lower().split('/')
    package_path = f'{"users" if owner_type == "User" else "orgs"}/{owner}/packages/container/{quote(package_name, safe="")}'
    package = api(package_path)
    exists = False
    if package is not None:
        exists = any(version in item.get('metadata', {}).get('container', {}).get('tags', []) for item in pages(package_path + '/versions'))
    if exists:
        run('docker', 'pull', remote)
        remote_id = subprocess.check_output(['docker', 'image', 'inspect', '--format', '{{.Id}}', remote], text=True).strip()
        if remote_id != container['image_id']: raise ValueError('Versão GHCR já existe com outros bytes.')
    else:
        run('docker', 'tag', container['image'], remote)
        run('docker', 'push', remote)
    # Se o pacote existia, sua visibilidade precisa permanecer a mesma após o push.
    package_visibility = check(repo, owner_type, os.environ['GH_TOKEN'],
                               allowed_visibilities=(before_visibility,) if before_visibility else allowed_visibility)
    digests = json.loads(subprocess.check_output(['docker', 'image', 'inspect', '--format', '{{json .RepoDigests}}', remote], text=True))
    immutable = next((item for item in digests if item.startswith(image + '@sha256:')), None)
    if not immutable: raise ValueError('Digest publicado não identificado.')
    source = folder / f'escritura-{version}-source.zip'
    run('git', 'archive', '--format=zip', f'--prefix=escritura-{version}/', '--output', source.resolve(), sha)
    files = [{'name': p.name, 'size': p.stat().st_size, 'sha256': digest(p)} for p in sorted(folder.iterdir()) if p.is_file() and p.name not in {'release.json', 'SHA256SUMS.txt'}]
    manifest = {'schema': 1, 'version': version, 'channel': channel, 'source_sha': sha, 'image': immutable, 'image_id': container['image_id'], 'package_visibility': package_visibility, 'files': files, 'run_url': f'https://github.com/{repo}/actions/runs/{os.getenv("GITHUB_RUN_ID", "")}', 'windows_subsystem': 'GUI', 'product_status': 'development-not-fiscally-homologated'}
    (folder / 'release.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    (folder / 'SHA256SUMS.txt').write_text(''.join(f'{digest(p)}  {p.name}\n' for p in sorted(folder.iterdir()) if p.is_file() and p.name != 'SHA256SUMS.txt'), encoding='utf-8')
    verify_release_files(folder, manifest, sha, version)
    if not tag: api(f'repos/{repo}/git/refs', 'POST', {'ref': f'refs/tags/{version}', 'sha': sha})
    if not current:
        current = api(f'repos/{repo}/releases', 'POST', {'tag_name': version, 'target_commitish': sha, 'name': f'Escritura {version}', 'draft': True, 'prerelease': channel == 'develop', 'generate_release_notes': True})
    if not current: raise RuntimeError('Não foi possível preparar release.')
    if current.get('target_commitish') not in (sha, branch): raise ValueError('Rascunho pertence a outra revisão.')
    # Somente rascunhos incompletos podem receber reenvio dos mesmos nomes.
    run('gh', 'release', 'upload', version, *[str(p) for p in sorted(folder.iterdir()) if p.is_file()], '--repo', repo, '--clobber')
    # Confere os bytes remotos antes de retirar o estado de rascunho.
    with tempfile.TemporaryDirectory() as temporary:
        run('gh', 'release', 'download', version, '--repo', repo, '--dir', temporary)
        downloaded = Path(temporary)
        remote_manifest = json.loads((downloaded / 'release.json').read_text(encoding='utf-8'))
        if remote_manifest != manifest: raise ValueError('Manifesto remoto divergente.')
        verify_release_files(downloaded, manifest, sha, version)
    latest = api(f'repos/{repo}/releases/latest') if channel == 'stable' else None
    newer = bool(latest and re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', latest['tag_name']) and parse(latest['tag_name']) > parse(version))
    ref = api(f'repos/{repo}/git/ref/heads/{branch}')
    promote = ref['object']['sha'] == sha and not newer
    # Aliases são promovidos a partir dos bytes já testados, nunca por rebuild.
    if promote:
        aliases = ['develop'] if channel == 'develop' else ['latest', '.'.join(version.split('.')[:2]), version.split('.')[0]]
        for alias in aliases:
            run('docker', 'tag', remote, f'{image}:{alias}')
            run('docker', 'push', f'{image}:{alias}')
    body = f'Fonte: `{sha}`\n\nImagem: `{immutable}`\n\nWindows gráfico x86/x64; extraia todo o ZIP. Confira SHA256SUMS.txt.\n\nProduto em desenvolvimento; executáveis sem assinatura Authenticode e sem homologação fiscal.\n\n' + (current.get('body') or '')
    api(f'repos/{repo}/releases/{current["id"]}', 'PATCH', {'draft': False, 'prerelease': channel == 'develop', 'make_latest': 'true' if channel == 'stable' and promote else 'false', 'body': body})
    print(f'Release publicada: https://github.com/{repo}/releases/tag/{version}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--sha', required=True)
    parser.add_argument('--channel', choices=['develop', 'stable'], required=True)
    parser.add_argument('--owner-type', choices=['User', 'Organization'], required=True)
    args = parser.parse_args()
    publish(args.assets, args.version, args.sha, args.channel, args.owner_type)


if __name__ == '__main__': main()
