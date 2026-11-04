"""Partial source reader and comparisons, never a Prosoft or fiscal validator."""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from decimal import Decimal
import re

XML_PROFILE = "nfe-4.00-header-billing-v3"
SPED_PROFILE = "efd-icms-ipi-020-c100-v1"


def document_fields(payload):
    """Comparable facts only; absence is never interpreted as zero or agreement."""
    result = {key: payload[key] for key in ("key", "model", "total", "issuer", "buyer", "content_fingerprint") if key in payload}
    for key in ("number", "series"):
        if payload.get(key) is not None:
            result[key] = str(int(payload[key]))
    issued = payload.get("issued_at") or payload.get("issued_date")
    if issued:
        result["issued_date"] = issued[:10]
    return result


def differences(observations):
    result = []
    keys = sorted({key for row in observations for key in row["normalized"]})
    for key in keys:
        values = [{"file_id": row["file_id"], "locator": row["locator"], "value": row["normalized"][key]}
                  for row in observations if key in row["normalized"]]
        if len({str(row["value"]) for row in values}) > 1:
            result.append({"field": key, "values": values})
    return result


def read_sped(content):
    """Tokenize, retaining source line and every original field for this profile."""
    try:
        text, encoding = content.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        text, encoding = content.decode("cp1252"), "cp1252"
    if "\x00" in text:
        raise ValueError("SPED contém caractere nulo")
    rows, counts = [], Counter()
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        if not line.startswith("|") or not line.endswith("|"):
            raise ValueError(f"Linha {number}: delimitadores SPED inválidos")
        fields = line[1:-1].split("|")
        if not re.fullmatch(r"[A-Z0-9]{4}", fields[0]):
            raise ValueError(f"Linha {number}: identificador de registro inválido")
        counts[fields[0]] += 1
        rows.append({"line": number, "record": fields[0], "fields": fields, "text": line})
    if not rows:
        raise ValueError("Nenhum registro SPED identificado")
    return rows, {"encoding": encoding, "record_counts": dict(counts)}


def _date(value, field):
    if not re.fullmatch(r"[0-9]{8}", value):
        raise ValueError(f"{field}: data deve usar DDMMAAAA")
    try:
        return datetime.strptime(value, "%d%m%Y").date().isoformat()
    except ValueError:
        raise ValueError(f"{field}: data inválida") from None


def _amount(value):
    if not re.fullmatch(r"[0-9]{1,15},[0-9]{2}", value):
        raise ValueError("VL_DOC: esperado valor sem milhar com vírgula e duas casas")
    return format(Decimal(value.replace(",", ".")), ".2f")


def parse_sped(content, company_cnpj, processing_competence):
    rows, metadata = read_sped(content)
    selected = [row for row in rows if row["record"] in {"0000", "C100", "C140", "C141"}]
    header_errors = []
    headers = [row for row in rows if row["record"] == "0000"]
    try:
        if len(headers) != 1 or rows[0]["record"] != "0000":
            raise ValueError("0000: esperado um único cabeçalho na primeira linha útil")
        fields = headers[0]["fields"]
        if len(fields) != 15:
            raise ValueError("0000: quantidade de campos incompatível com o perfil")
        if fields[1] != "020":
            raise ValueError("COD_VER: somente versão 020 neste perfil parcial")
        start, end = _date(fields[3], "DT_INI"), _date(fields[4], "DT_FIN")
        if start > end or start[:7] != end[:7] or start[:7] != processing_competence or start[:4] != "2026":
            raise ValueError("DT_INI/DT_FIN: período diverge dos movimentos ou da vigência do perfil 020")
        if not company_cnpj or fields[6] != company_cnpj or fields[7]:
            raise ValueError("CNPJ: cabeçalho não confere com a empresa cadastrada")
    except ValueError as exc:
        header_errors.append(str(exc))
    current_document = None
    block_c_open = False
    for row in selected:
        row.update(normalized={}, issues=[], parent_line=None)
    selected_by_line = {row["line"]: row for row in selected}
    for original in rows:
        record = original["record"]
        if record == "C001":
            block_c_open = original["fields"] == ["C001", "0"]
        elif record == "C990" or not record.startswith("C"):
            block_c_open = False
            current_document = None
        row = selected_by_line.get(original["line"])
        if row is None:
            if record.startswith("C") and not record.startswith("C1") and record != "C001":
                current_document = None
            continue
        row["issues"].extend(header_errors)
        if record == "0000":
            continue
        if record in {"C140", "C141"}:
            row["parent_line"] = current_document
            row["issues"].append("C140/C141: somente preservação; interpretação para modelo 55 depende de perfil Prosoft confirmado")
            continue
        current_document = row["line"]
        fields = row["fields"]
        if header_errors:
            continue
        try:
            if not block_c_open:
                raise ValueError("C100: abertura C001 com movimentos ausente")
            if len(fields) != 29:
                raise ValueError("C100: quantidade de campos incompatível com o perfil")
            if fields[4] != "55" or fields[5] != "00":
                raise ValueError("COD_MOD/COD_SIT: somente NF-e 55 regular 00 neste recorte")
            if fields[1] not in {"0", "1"} or fields[2] not in {"0", "1"}:
                raise ValueError("IND_OPER/IND_EMIT: indicador inválido")
            key, series, number = fields[8], fields[6], fields[7]
            if not re.fullmatch(r"[0-9]{44}", key):
                raise ValueError("CHV_NFE: ausente ou inválida; possível duplicidade exige conferência")
            if not re.fullmatch(r"[0-9]{3}", series) or not re.fullmatch(r"[0-9]{1,9}", number) or int(number) == 0:
                raise ValueError("SER/NUM_DOC: identificação inválida")
            emitted = _date(fields[9], "DT_DOC")
            if emitted[:7] != processing_competence:
                raise ValueError("DT_DOC: competência de emissão diverge; nenhum transporte automático de movimentos")
            dv = 11 - sum(int(d) * (2 + i % 8) for i, d in enumerate(reversed(key[:43]))) % 11
            dv = 0 if dv >= 10 else dv
            if int(key[-1]) != dv or key[20:22] != "55" or key[22:25] != series or key[25:34] != number.zfill(9) or key[2:6] != emitted[2:4] + emitted[5:7]:
                raise ValueError("CHV_NFE: incoerência com campos ou dígito verificador")
            if fields[2] == "0" and key[6:20] != company_cnpj:
                raise ValueError("IND_EMIT/CHV_NFE: emissão própria não identifica a empresa")
            row["normalized"] = {"key": key, "model": "55", "series": series, "number": number,
                                 "issued_date": emitted, "total": _amount(fields[11]), "issuer": key[6:20]}
        except ValueError as exc:
            row["issues"].append(str(exc))
    key_counts = Counter(row["normalized"].get("key") for row in selected if row["normalized"])
    for row in selected:
        key = row["normalized"].get("key")
        if key and key_counts[key] > 1:
            row["issues"].append("CHV_NFE: documento repetido no mesmo arquivo; conferir registros")
    metadata.update(profile=SPED_PROFILE, partial=True, header_issues=header_errors)
    return selected, metadata
