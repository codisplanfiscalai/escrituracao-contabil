"""Build official libarchive + static liblzma for each Windows architecture."""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'packaging/native-archives.lock.json'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(archive, destination):
    with tarfile.open(archive) as tar:
        for member in tar:
            path = Path(member.name)
            if path.is_absolute() or '..' in path.parts or '\\' in member.name or not (member.isdir() or member.isfile()):
                raise ValueError('Entrada insegura no pacote de fontes')
            target = destination / path
            if member.isdir(): target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as source, target.open('wb') as output:
                    shutil.copyfileobj(source, output)


def sources(directory):
    lock = json.loads(LOCK.read_text(encoding='utf-8'))
    if lock['schema'] != 1 or set(lock['sources']) != {'libarchive', 'xz'}: raise ValueError('Lock inválido')
    directory.mkdir(parents=True, exist_ok=True)
    result = {}
    for name, item in lock['sources'].items():
        repo = {'libarchive': 'libarchive/libarchive', 'xz': 'tukaani-project/xz'}[name]
        version = item['version']
        if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version): raise ValueError('Versão inválida')
        url = f'https://github.com/{repo}/releases/download/v{version}/{name}-{version}.tar.gz'
        if item['url'] != url or not re.fullmatch(r'[0-9a-f]{64}', item['sha256']): raise ValueError('Origem não oficial ou hash inválido')
        archive = directory / f'{name}-{version}.tar.gz'
        if not archive.exists():
            temporary = archive.with_suffix('.download')
            with urlopen(url, timeout=60) as response, temporary.open('wb') as output:
                shutil.copyfileobj(response, output)
            if sha(temporary) != item['sha256']:
                temporary.unlink()
                raise ValueError('Hash da fonte divergente')
            temporary.replace(archive)
        if sha(archive) != item['sha256']: raise ValueError('Cache de fontes divergente')
        path = directory / f'{name}-{version}'
        # Always derive build inputs from the verified archive, never a mutable cached tree.
        if path.exists(): shutil.rmtree(path)
        extract(archive, directory)
        for filename, expected in item['licenses'].items():
            if filename not in {'COPYING', 'COPYING.0BSD'} or sha(path / filename) != expected:
                raise ValueError('Licença oficial divergente')
        result[name] = path
    return result, lock


def run(*command):
    print('+', *map(str, command), flush=True)
    subprocess.run(list(map(str, command)), check=True)


def build(arch):
    if sys.platform != 'win32': raise ValueError('Build nativo Windows obrigatório')
    base = ROOT / 'build/native' / arch
    paths, lock = sources(ROOT / 'build/native/sources')
    prefix = base / 'lzma-install'
    generator = ['-G', 'Visual Studio 17 2022', '-A', {'x86':'Win32','x64':'x64'}[arch]]
    common = ['-DCMAKE_POLICY_DEFAULT_CMP0091=NEW', '-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded']
    run('cmake', '-S', paths['xz'], '-B', base/'xz', *generator, *common,
        '-DBUILD_SHARED_LIBS=OFF', '-DBUILD_TESTING=OFF', '-DXZ_NLS=OFF', '-DXZ_DOC=OFF',
        '-DXZ_TOOL_XZ=OFF', '-DXZ_TOOL_XZDEC=OFF', '-DXZ_TOOL_LZMADEC=OFF', '-DXZ_TOOL_LZMAINFO=OFF',
        f'-DCMAKE_INSTALL_PREFIX={prefix}')
    run('cmake', '--build', base/'xz', '--config', 'Release', '--target', 'install', '--parallel', '2')
    disabled = ['OPENSSL','MBEDTLS','NETTLE','LIBB2','LZ4','LZO','ZSTD','ZLIB','BZip2','LIBXML2','BSDXML','EXPAT',
                'WIN32_XMLLITE','PCREPOSIX','PCRE2POSIX','LIBGCC','CNG','TAR','CPIO','CAT','UNZIP','XATTR','ACL','ICONV','TEST']
    run('cmake', '-S', paths['libarchive'], '-B', base/'libarchive', *generator, *common,
        '-DBUILD_SHARED_LIBS=ON', '-DBUILD_TESTING=OFF', '-DMSVC_USE_STATIC_CRT=ON',
        '-DENABLE_LZMA=ON', f'-DLIBLZMA_LIBRARY={prefix / "lib/lzma.lib"}',
        f'-DLIBLZMA_INCLUDE_DIR={prefix / "include"}', *[f'-DENABLE_{option}=OFF' for option in disabled])
    cache = (base/'libarchive/config.h').read_text()
    if not re.search(r'^#define HAVE_LZMA_H 1$', cache, re.M): raise ValueError('liblzma não foi ligada')
    run('cmake', '--build', base/'libarchive', '--config', 'Release', '--target', 'archive', '--parallel', '2')
    package = base/'package'; package.mkdir(parents=True, exist_ok=True)
    dlls = list((base/'libarchive').rglob('archive.dll'))
    if len(dlls) != 1: raise ValueError('DLL libarchive ausente/ambígua')
    shutil.copy2(dlls[0], package/'archive.dll')
    import pefile
    pe = pefile.PE(str(package/'archive.dll'))
    if pe.FILE_HEADER.Machine != {'x86':0x14c,'x64':0x8664}[arch]: raise ValueError('Arquitetura DLL divergente')
    imports = [item.dll.decode('ascii').lower() for item in pe.DIRECTORY_ENTRY_IMPORT]
    allowed = {'kernel32.dll','advapi32.dll','bcrypt.dll','user32.dll','crypt32.dll','ntdll.dll','ws2_32.dll','normaliz.dll','ucrtbase.dll'}
    if any(name not in allowed and not name.startswith('api-ms-win-') for name in imports):
        raise ValueError(f'Dependências DLL não previstas: {imports}')
    lib = ctypes.CDLL(str((package/'archive.dll').resolve()))
    lib.archive_version_number.restype = ctypes.c_int
    if lib.archive_version_number() != 3008011: raise ValueError('Versão nativa incorreta')
    notices = package/'licenses'; notices.mkdir(exist_ok=True)
    for name, path in paths.items():
        for filename in lock['sources'][name]['licenses']:
            shutil.copy2(path/filename, notices/f'{name}-{filename}.txt')
    # Preserve complete source-file notices, including BSD-3-Clause and public-domain/CC0 exceptions.
    blocks = []
    for path in sorted((paths['libarchive']/'libarchive').glob('*')):
        if path.suffix in {'.c','.h'}:
            text = path.read_text(encoding='utf-8', errors='strict')
            prefix = text.split('#include',1)[0]
            comments = re.findall(r'/\*.*?\*/', prefix, re.S)
            if comments: blocks.append(path.name+'\n'+'\n'.join(comments))
    (notices/'libarchive-source-notices.txt').write_text('\n\n'.join(blocks)+'\n', encoding='utf-8')
    manifest = {'schema':1, 'architecture':arch, 'sources':lock['sources'], 'imports':imports,
                'files':{p.relative_to(package).as_posix():sha(p) for p in package.rglob('*') if p.is_file() and p.name!='native-manifest.json'}}
    (package/'native-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n', encoding='utf-8')
    return package


if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--arch', choices=['x86','x64'], required=True)
    build(parser.parse_args().arch)
