"""Bounded archive reader. No member is ever extracted to a filesystem path."""
import base64
import lzma
import zlib
import ctypes
import ctypes.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import subprocess
import sys
import tempfile
import zipfile

MAX_MEMBERS = 500
MAX_MEMBER_BYTES = 10 * 1024 * 1024
MAX_EXPANDED_BYTES = 100 * 1024 * 1024
MAX_RATIO = 100
ARCHIVE_TIMEOUT = 20


def safe_member(name):
    if not isinstance(name, str) or not name or len(name) > 1000 or any(ord(c) < 32 for c in name):
        raise ValueError('Nome interno ausente, longo ou com caractere de controle')
    normalized = name.replace('\\', '/')
    if normalized.startswith('/') or re.match(r'^[a-zA-Z]:', normalized) or ':' in normalized or '..' in normalized.split('/'):
        raise ValueError('Caminho interno inseguro')
    if not PurePosixPath(normalized).name or normalized in {'.', '..'}:
        raise ValueError('Nome interno inválido')
    return str(PurePosixPath(normalized))


def _check_zip_directory(content):
    # Inspect the bounded central directory before ZipFile allocates ZipInfo objects.
    # ZIP64/multipart are deliberately outside this small-upload profile.
    end = content.rfind(b'PK\x05\x06', max(0, len(content) - 65557))
    if end < 0 or end + 22 > len(content):
        raise ValueError('Diretório ZIP ausente')
    _, disk, directory_disk, on_disk, count, size, offset, comment = struct.unpack_from('<4s4H2IH', content, end)
    if disk or directory_disk or on_disk != count or count > MAX_MEMBERS or size == 0xffffffff or offset == 0xffffffff:
        raise ValueError('ZIP multipartes, ZIP64 ou limite de entradas não suportado')
    if end + 22 + comment != len(content) or size > end:
        raise ValueError('Diretório ZIP inconsistente')
    position, actual = end - size, 0
    while position < end:
        if position + 46 > end or content[position:position+4] != b'PK\x01\x02':
            raise ValueError('Diretório ZIP inválido')
        name, extra, note = struct.unpack_from('<3H', content, position + 28)
        position += 46 + name + extra + note
        actual += 1
        if actual > MAX_MEMBERS:
            raise ValueError('Pacote excede 500 entradas')
    if position != end or actual != count:
        raise ValueError('Contagem ZIP inconsistente')


def _zip_members(content):
    _check_zip_directory(content)
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_MEMBERS:
            raise ValueError('Pacote excede 500 entradas')
        budget = min(MAX_EXPANDED_BYTES, len(content) * MAX_RATIO)
        if sum(info.file_size for info in infos if not info.is_dir()) > budget:
            raise ValueError('Pacote excede limite total de expansão')
        total = 0
        for info in infos:
            name = info.orig_filename
            try:
                safe_member(name)
                mode = info.external_attr >> 16
                if info.is_dir() and stat.S_IFMT(mode) in {0, stat.S_IFDIR}:
                    continue
                if stat.S_IFMT(mode) not in {0, stat.S_IFREG}:
                    raise ValueError('Link ou entrada especial não permitida')
                if info.flag_bits & 1:
                    raise ValueError('Arquivo criptografado não suportado')
                if info.file_size > MAX_MEMBER_BYTES or info.file_size > max(1, info.compress_size) * MAX_RATIO:
                    raise ValueError('Arquivo excede limite de tamanho ou razão de compressão')
                if total + info.file_size > budget:
                    raise ValueError('Pacote excede limite total de expansão')
                with archive.open(info) as stream:
                    data = stream.read(min(MAX_MEMBER_BYTES, budget - total) + 1)
                if len(data) != info.file_size or len(data) > MAX_MEMBER_BYTES:
                    raise ValueError('Tamanho descomprimido inconsistente ou excessivo')
                total += len(data)
                yield {'name': name, 'content': data}
            except (ValueError, RuntimeError, OSError, zipfile.BadZipFile, NotImplementedError, EOFError, zlib.error, lzma.LZMAError):
                # Do not leak decoder internals; preserve package bytes and entry identity.
                yield {'name': name, 'error': 'Entrada insegura, criptografada, corrompida ou acima dos limites'}


def native_library():
    if sys.platform == 'win32':
        # Absolute bundled path only; never search CWD/PATH for native code.
        directory = Path(__file__).resolve().parent / 'native'
        if not getattr(sys, 'frozen', False) and os.getenv('ESCRITURA_LIBARCHIVE_DIR'):
            directory = Path(os.environ['ESCRITURA_LIBARCHIVE_DIR']).resolve()
        library = directory / 'archive.dll'
        if not library.is_file():
            raise ValueError('Leitor libarchive indisponível nesta instalação Windows')
        library = str(library)
    else:
        library = ctypes.util.find_library('archive')
    if not library:
        raise ValueError('Leitor libarchive indisponível para 7z/RAR nesta instalação')
    return library


def _native_members(content, kind):
    lib = ctypes.CDLL(native_library())
    def bind(name, result, *args):
        fn = getattr(lib, name); fn.restype = result; fn.argtypes = args
        return fn
    ptr = ctypes.c_void_p
    new = bind('archive_read_new', ptr)
    free = bind('archive_read_free', ctypes.c_int, ptr)
    support = bind('archive_read_support_format_' + ('7zip' if kind == '7Z' else 'rar'), ctypes.c_int, ptr)
    open_memory = bind('archive_read_open_memory', ctypes.c_int, ptr, ptr, ctypes.c_size_t)
    next_header = bind('archive_read_next_header', ctypes.c_int, ptr, ctypes.POINTER(ptr))
    pathname = bind('archive_entry_pathname_utf8', ctypes.c_char_p, ptr)
    size = bind('archive_entry_size', ctypes.c_int64, ptr)
    filetype = bind('archive_entry_filetype', ctypes.c_uint, ptr)
    symlink = bind('archive_entry_symlink', ctypes.c_char_p, ptr)
    hardlink = bind('archive_entry_hardlink', ctypes.c_char_p, ptr)
    encrypted = bind('archive_entry_is_encrypted', ctypes.c_int, ptr)
    read = bind('archive_read_data', ctypes.c_ssize_t, ptr, ptr, ctypes.c_size_t)
    archive = new()
    if not archive:
        raise ValueError('Não foi possível iniciar o leitor do pacote')
    raw = ctypes.create_string_buffer(content)
    try:
        support(archive)
        if kind == 'RAR' and hasattr(lib, 'archive_read_support_format_rar5'):
            bind('archive_read_support_format_rar5', ctypes.c_int, ptr)(archive)
        if open_memory(archive, raw, len(content)) != 0:
            raise ValueError('Pacote corrompido, criptografado ou formato não suportado')
        total = 0
        budget = min(MAX_EXPANDED_BYTES, len(content) * MAX_RATIO)
        buffer = ctypes.create_string_buffer(64 * 1024)
        for _ in range(MAX_MEMBERS + 1):
            entry = ptr()
            code = next_header(archive, ctypes.byref(entry))
            if code == 1:
                return
            if code != 0:
                raise ValueError('Cabeçalho corrompido ou recurso do pacote não suportado')
            if _ == MAX_MEMBERS:
                raise ValueError('Pacote excede 500 entradas')
            raw_name = pathname(entry)
            name = raw_name.decode('utf-8', errors='strict') if raw_name else ''
            safe_member(name)
            if symlink(entry) or hardlink(entry) or encrypted(entry):
                raise ValueError('Link ou criptografia não permitido no pacote')
            if filetype(entry) == stat.S_IFDIR:
                continue
            expected = size(entry)
            if filetype(entry) != stat.S_IFREG or expected < 0 or expected > MAX_MEMBER_BYTES or total + expected > budget:
                raise ValueError('Entrada especial ou limite de expansão excedido')
            data = bytearray()
            while True:
                count = read(archive, buffer, len(buffer))
                if count < 0:
                    raise ValueError('Dados corrompidos ou compressão não suportada')
                if count == 0:
                    break
                total += count
                if total > budget or len(data) + count > MAX_MEMBER_BYTES:
                    raise ValueError('Limite de expansão excedido')
                data.extend(buffer.raw[:count])
            if len(data) != expected:
                raise ValueError('Tamanho descomprimido inconsistente')
            yield {'name': name, 'content': bytes(data)}
    finally:
        free(archive)


def archive_members(content, kind, timeout=ARCHIVE_TIMEOUT):
    """Decode in a bounded child; no archive-controlled filesystem extraction."""
    if kind == 'ZIP':
        try:
            return list(_zip_members(content))
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            raise ValueError('ZIP inválido ou acima dos limites') from exc
    if kind not in {'7Z', 'RAR'} or len(content) > MAX_MEMBER_BYTES:
        raise ValueError('Formato ou tamanho de pacote inválido')
    from src.archive_limits import OUTPUT_BYTES
    with tempfile.TemporaryDirectory(prefix='escritura-reader-') as directory:
        source, output = Path(directory) / 'input', Path(directory) / 'output'
        source.write_bytes(content)
        output.touch(mode=0o600, exist_ok=False)
        frozen = getattr(sys, 'frozen', False)
        command = [sys.executable, '--archive-worker'] if frozen else [sys.executable, '-m', 'src.archive_worker']
        environment = os.environ.copy()
        if not frozen:
            environment['PYTHONPATH'] = str(Path(__file__).resolve().parents[1])
        try:
            result = subprocess.run([*command, kind, str(source), str(output)],
                                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, env=environment,
                                    creationflags=0x08000000 if sys.platform == 'win32' else 0,
                                    timeout=max(0.1, min(ARCHIVE_TIMEOUT, timeout)), check=False)
        except subprocess.TimeoutExpired as exc:
            raise ValueError('Pacote excede tempo máximo de leitura (20 segundos)') from exc
        if result.returncode or output.stat().st_size > OUTPUT_BYTES:
            raise ValueError('Pacote 7z/RAR recusado: leitor indisponível, formato incompatível, corrupção ou limite de segurança')
        members, total = [], 0
        budget = min(MAX_EXPANDED_BYTES, len(content) * MAX_RATIO)
        try:
            with output.open('rb') as handle:
                while True:
                    line = handle.readline(2 * MAX_MEMBER_BYTES + 20000)
                    if not line: break
                    if not line.endswith(b'\n') or len(members) >= MAX_MEMBERS:
                        raise ValueError('Saída do leitor acima dos limites')
                    value = json.loads(line)
                    if set(value) != {'name', 'content'}: raise ValueError('Saída inválida')
                    safe_member(value['name'])
                    data = base64.b64decode(value['content'], validate=True)
                    total += len(data)
                    if len(data) > MAX_MEMBER_BYTES or total > budget:
                        raise ValueError('Saída do leitor acima dos limites')
                    members.append({'name': value['name'], 'content': data})
        except (ValueError, TypeError, KeyError, UnicodeError) as exc:
            raise ValueError('Saída do leitor inválida ou acima dos limites') from exc
        return members
