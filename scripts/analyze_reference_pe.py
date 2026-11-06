"""Bounded PE triage using only byte reads. Never loads or executes the target.

Reference files and output must stay outside the repository. Technology hints
are evidence, not recovery of source code or proof of application behavior.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

MAX_BYTES = 64 * 1024 * 1024
ROOT = Path(__file__).resolve().parents[1]


def analyze_bytes(data):
    if not isinstance(data, bytes) or not 64 <= len(data) <= MAX_BYTES:
        raise ValueError('Arquivo vazio, curto demais ou acima de 64 MiB')

    def read(fmt, offset):
        if offset < 0 or offset + struct.calcsize(fmt) > len(data):
            raise ValueError('Estrutura PE truncada ou fora dos limites')
        return struct.unpack_from(fmt, data, offset)

    if data[:2] != b'MZ':
        raise ValueError('Assinatura DOS MZ ausente')
    pe, = read('<I', 60)
    if pe < 64 or data[pe:pe + 4] != b'PE\x00\x00':
        raise ValueError('Assinatura PE ausente ou posição inválida')
    machine, count, timestamp, _, _, optional_size, flags = read('<HHIIIHH', pe + 4)
    if not 1 <= count <= 96:
        raise ValueError('Quantidade de seções fora do limite de triagem')
    opt = pe + 24
    magic, = read('<H', opt)
    if magic not in {0x10b, 0x20b}:
        raise ValueError('Formato opcional PE não suportado')
    directory_offset = 96 if magic == 0x10b else 112
    if optional_size < directory_offset or opt + optional_size > len(data):
        raise ValueError('Cabeçalho opcional truncado')
    directory_count, = read('<I', opt + directory_offset - 4)

    def directory(index):
        if directory_count <= index or optional_size < directory_offset + (index + 1) * 8:
            return (0, 0)
        return read('<II', opt + directory_offset + index * 8)

    sections = []
    for index in range(count):
        at = opt + optional_size + index * 40
        name, virtual_size, rva, raw_size, raw_at, _, _, _, _, characteristics = read('<8sIIIIIIHHI', at)
        if raw_size and (raw_at < 0 or raw_at + raw_size > len(data)):
            raise ValueError('Seção PE aponta para bytes ausentes')
        sections.append({'name': name.rstrip(b'\x00').decode('ascii', 'replace'), 'rva': rva,
                         'virtual_size': virtual_size, 'raw_size': raw_size, 'raw_offset': raw_at,
                         'characteristics': characteristics})

    headers_size, = read('<I', opt + 60)

    def offset(rva, length=1):
        if rva < min(headers_size, len(data)) and rva + length <= min(headers_size, len(data)):
            return rva
        for section in sections:
            delta = rva - section['rva']
            if 0 <= delta and delta + length <= section['raw_size']:
                return section['raw_offset'] + delta
        raise ValueError('RVA não mapeado nos bytes do arquivo')

    imports = []
    import_rva, import_size = directory(1)
    if import_rva:
        for index in range(min(import_size // 20, 512)):
            values = read('<IIIII', offset(import_rva + index * 20, 20))
            if not any(values):
                break
            name_at = offset(values[3])
            end = data.find(b'\x00', name_at, min(name_at + 256, len(data)))
            if end < 0:
                raise ValueError('Nome de DLL sem terminador dentro do limite')
            imports.append(data[name_at:end].decode('ascii', 'replace'))

    hints = []
    clr_rva, clr_size = directory(14)
    if clr_rva and clr_size >= 72:
        offset(clr_rva, 72)
        hints.append({'technology': '.NET/CLR', 'evidence': 'Diretório CLR presente; linguagem de origem não determinada'})
    for name in imports:
        if re.fullmatch(r'msvbvm[56]0\.dll', name, re.I):
            hints.append({'technology': 'Visual Basic runtime', 'evidence': name})
        if re.fullmatch(r'python\d+\.dll', name, re.I):
            hints.append({'technology': 'Python runtime', 'evidence': name})
    markers = [m for m in (b'Borland', b'Delphi', b'TApplication', b'TPF0') if m in data]
    if len(markers) >= 2:
        hints.append({'technology': 'Possível Delphi/Borland', 'evidence': [m.decode() for m in markers], 'limit': 'Strings não confirmam compilador ou regras do programa'})
    if b'MEI\x0c\x0b\x0a\x0b\x0e' in data:
        hints.append({'technology': 'Possível PyInstaller', 'evidence': 'Marcador de arquivo empacotado; conteúdo não extraído'})
    return {'size_bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'format': 'PE32' if magic == 0x10b else 'PE32+',
            'machine': hex(machine), 'coff_timestamp_unverified': timestamp,
            'subsystem': read('<H', opt + 68)[0], 'coff_characteristics': flags,
            'sections': sections, 'imported_dlls': sorted(set(imports)),
            'resources_directory_present': bool(directory(2)[0]), 'technology_hints': hints,
            'source_code_recovered': False, 'execution_performed': False,
            'limits': ['Não valida assinatura ou comportamento', 'Ausência de indícios não determina linguagem',
                       'Não recupera automaticamente telas, banco, regras ou código-fonte completo']}


def outside_repository(path):
    resolved = Path(path).resolve()
    if resolved == ROOT or ROOT in resolved.parents:
        raise ValueError('Referências e relatórios de binários devem ficar fora do repositório')
    return resolved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', nargs='+', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output = outside_repository(args.output)
    results = []
    for source in args.inputs:
        source = outside_repository(source)
        if source.stat().st_size > MAX_BYTES:
            raise ValueError('Arquivo acima de 64 MiB')
        try:
            with source.open('rb') as handle:
                data = handle.read(MAX_BYTES + 1)
            results.append({'filename': source.name, **analyze_bytes(data)})
        except ValueError as error:
            results.append({'filename': source.name, 'error': str(error), 'execution_performed': False})
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
    output.chmod(0o600)


if __name__ == '__main__':
    main()
