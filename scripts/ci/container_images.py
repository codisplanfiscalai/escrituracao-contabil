"""Inventário e espelhamento explícito das imagens reais; plan não acessa a rede."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / 'packaging/container-images.lock.json'


def load_lock(path=LOCK):
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema') != 1 or set(data.get('images', {})) != {'python', 'caddy'}:
        raise ValueError('Inventário de imagens inválido.')
    for name, item in data['images'].items():
        digest = item['digest']
        if not re.fullmatch(r'sha256:[a-f0-9]{64}', digest):
            raise ValueError('Digest inválido.')
        if not re.fullmatch(r'docker.io/library/' + name + r':[a-zA-Z0-9_.-]+@' + digest, item['upstream']):
            raise ValueError('Origem não fixada por digest.')
        if not re.fullmatch(r'ghcr.io/codisplanfiscalai/escrituracao-contabil-deps/' + name + r':[a-zA-Z0-9_.-]+-' + digest[7:19], item['mirror']):
            raise ValueError('Destino fora do namespace ou versão permitidos.')
    return data


def image_ref(item, source):
    if source == 'upstream': return item['upstream']
    if source == 'ghcr': return item['mirror'] + '@' + item['digest']
    raise ValueError('Origem desconhecida; fallback implícito não é permitido.')


def inspect(reference, *, allow_missing=False):
    result = subprocess.run(['skopeo', 'inspect', '--raw', 'docker://' + reference], capture_output=True)
    if result.returncode:
        error = result.stderr.decode('utf-8', errors='replace')
        # Apenas ausência explícita do manifesto. Autenticação/rede nunca viram ausência.
        if allow_missing and re.search(r'(?i)manifest unknown|manifest_unknown', error):
            return None
        raise RuntimeError(f'Falha ao consultar {reference}: {error}')
    return 'sha256:' + hashlib.sha256(result.stdout).hexdigest()


def verify(item, source):
    actual = inspect(image_ref(item, source))
    if actual != item['digest']:
        raise ValueError(f'Digest divergente: {image_ref(item, source)}')


def mirror(item, *, publish=False):
    if not publish:
        raise ValueError('Espelhamento exige --publish e autorização de publicação.')
    # Verifica a tag antes de qualquer escrita e nunca substitui bytes divergentes.
    existing = inspect(item['mirror'], allow_missing=True)
    if existing is not None:
        if existing != item['digest']:
            raise ValueError('Versão GHCR existente com outros bytes; não sobrescrever.')
        verify(item, 'ghcr')
        return
    verify(item, 'upstream')
    subprocess.run(['skopeo', 'copy', '--all', '--preserve-digests',
                    'docker://' + item['upstream'], 'docker://' + item['mirror']], check=True)
    verify(item, 'ghcr')
    if inspect(item['mirror']) != item['digest']:
        raise ValueError('Tag publicada não corresponde ao digest esperado.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['plan', 'verify', 'mirror', 'env'])
    parser.add_argument('--source', choices=['upstream', 'ghcr'], default='ghcr')
    parser.add_argument('--publish', action='store_true', help='Escrita remota; requer autorização prévia')
    args = parser.parse_args()
    images = load_lock()['images']
    if args.command == 'plan':
        print(json.dumps(images, indent=2))
    elif args.command == 'env':
        print('ESCRITURA_PROXY_IMAGE=' + image_ref(images['caddy'], args.source))
        print('PYTHON_IMAGE=' + image_ref(images['python'], args.source))
    else:
        for name, item in images.items():
            if args.command == 'mirror': mirror(item, publish=args.publish)
            else: verify(item, args.source)
            print(f'{name}: digest verificado')


if __name__ == '__main__': main()
