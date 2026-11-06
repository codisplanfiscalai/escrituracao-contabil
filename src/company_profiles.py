"""Client registration and the application's own organization have separate identities.

These are declarations for registration, never tax or payroll calculation policies.
No existing company is silently classified as the application's own organization.
"""
import json
import re
from datetime import date

from .accounting_store import digest, identifier

PROFILE_SCHEMA = """
CREATE TABLE IF NOT EXISTS client_profile_versions (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 version INTEGER NOT NULL, data TEXT NOT NULL, snapshot_hash TEXT NOT NULL,
 actor TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(company_id,version));
CREATE TABLE IF NOT EXISTS user_organization_versions (
 version INTEGER PRIMARY KEY, data TEXT NOT NULL, snapshot_hash TEXT NOT NULL,
 actor TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL);
"""

PROFILE_FIELDS = [
    {"id": "basic", "label": "Dados básicos", "fields": [
        ["trade_name", "Nome fantasia"], ["phone", "Telefone"], ["email", "E-mail"],
        ["postal_code", "CEP"], ["street", "Logradouro"], ["number", "Número"],
        ["complement", "Complemento"], ["district", "Bairro"], ["city", "Município"],
        ["state", "UF"], ["municipality_code", "Código IBGE do município"],
        ["start_date", "Data de início das atividades"]]},
    {"id": "fiscal", "label": "Dados fiscais", "fields": [
        ["state_registration", "Inscrição estadual"], ["municipal_registration", "Inscrição municipal"],
        ["cnae", "CNAE principal"], ["tax_regime", "Regime tributário declarado"],
        ["crt", "CRT declarado"], ["activity", "Atividade"]]},
    {"id": "labor", "label": "Dados trabalhistas", "fields": [
        ["social_security_code", "Código de recolhimento previdenciário"], ["fpas", "FPAS"],
        ["third_parties_code", "Código de terceiros"], ["rat", "RAT informado"],
        ["fap", "FAP informado"], ["union", "Sindicato"]]},
    {"id": "accounting", "label": "Dados contábeis", "fields": [
        ["bookkeeping_type", "Forma de escrituração"], ["accountant_name", "Contabilista responsável"],
        ["accountant_tax_id", "CPF/CNPJ do contabilista"], ["crc", "CRC"],
        ["fiscal_year_end", "Encerramento do exercício informado"]]},
    {"id": "general", "label": "Dados gerais", "fields": [
        ["contact_name", "Contato responsável"], ["notes", "Observações"]]},
]


def empty_profile():
    return {s["id"]: {key: "" for key, _ in s["fields"]} for s in PROFILE_FIELDS}


def validate_profile(data):
    from .persistence import _text
    if not isinstance(data, dict) or set(data) - set(empty_profile()):
        raise ValueError("Seções cadastrais desconhecidas")
    result = empty_profile()
    for section in PROFILE_FIELDS:
        section_id = section["id"]
        values = data.get(section_id, {})
        if not isinstance(values, dict) or set(values) - set(result[section_id]):
            raise ValueError("Campos cadastrais desconhecidos")
        for key, label in section["fields"]:
            result[section_id][key] = _text(values.get(key, ""), label, 2000 if key == "notes" else 200, False)
    basic = result["basic"]
    for key, pattern in [("postal_code", r"\d{8}"), ("state", r"[A-Z]{2}"), ("municipality_code", r"\d{7}")]:
        if basic[key] and not re.fullmatch(pattern, basic[key]):
            raise ValueError("CEP: 8 dígitos; UF: 2 letras maiúsculas; IBGE: 7 dígitos")
    if basic["email"] and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", basic["email"]):
        raise ValueError("E-mail inválido")
    if basic["start_date"]:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", basic["start_date"]):
            raise ValueError("Data inicial deve usar AAAA-MM-DD")
        date.fromisoformat(basic["start_date"])
    return result


def expected_version(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("Versão cadastral deve ser inteiro não negativo")
    return value


class CompanyProfilesMixin:
    @staticmethod
    def _registration(row):
        result = dict(row)
        result["data"] = json.loads(result["data"])
        if digest(result["data"]) != result["snapshot_hash"]:
            raise ValueError("Histórico cadastral alterado")
        return result

    def client_profile(self, company_id):
        company = self._company(identifier(company_id))
        row = self.db.execute("SELECT * FROM client_profile_versions WHERE company_id=? ORDER BY version DESC LIMIT 1", (company["id"],)).fetchone()
        result = self._registration(row) if row else {"version": 0, "data": empty_profile()}
        return {**result, "company": company, "fields": PROFILE_FIELDS}

    def client_profile_history(self, company_id):
        self._company(identifier(company_id))
        return [self._registration(row) for row in self.db.execute("SELECT * FROM client_profile_versions WHERE company_id=? ORDER BY version DESC", (company_id,))]

    def save_client_profile(self, company_id, data, version, reason):
        from .persistence import _json, _text
        company_id = identifier(company_id)
        data = validate_profile(data)
        version = expected_version(version)
        reason = _text(reason, "Motivo cadastral", 1000)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            current = self.client_profile(company_id)
            if current["version"] != version:
                raise ValueError("Cadastro alterado; recarregue antes de salvar")
            self.db.execute("INSERT INTO client_profile_versions(company_id,version,data,snapshot_hash,actor,reason,created_at) VALUES(?,?,?,?,?,?,?)", (company_id, version + 1, _json(data), digest(data), self.actor, reason, self._now()))
            self._audit(company_id, "cadastro_cliente_versionado", {"version": version + 1, "reason": reason})
        return self.client_profile(company_id)

    def user_organization(self):
        row = self.db.execute("SELECT * FROM user_organization_versions ORDER BY version DESC LIMIT 1").fetchone()
        result = self._registration(row) if row else {"version": 0, "data": {"name": "", "cnpj": "", "profile": empty_profile()}}
        return {**result, "fields": PROFILE_FIELDS}

    def save_user_organization(self, data, version, reason):
        from .persistence import _json, _text
        if not isinstance(data, dict) or set(data) != {"name", "cnpj", "profile"}:
            raise ValueError("Informe nome, CNPJ e perfil da empresa usuária")
        name = _text(data["name"], "Nome da empresa usuária", 200)
        cnpj = _text(data["cnpj"], "CNPJ", 14, False)
        if cnpj and not re.fullmatch(r"\d{14}", cnpj):
            raise ValueError("CNPJ deve conter 14 dígitos; autenticidade não verificada")
        data = {"name": name, "cnpj": cnpj, "profile": validate_profile(data["profile"])}
        version = expected_version(version)
        reason = _text(reason, "Motivo cadastral", 1000)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            if self.user_organization()["version"] != version:
                raise ValueError("Empresa usuária alterada; recarregue antes de salvar")
            self.db.execute("INSERT INTO user_organization_versions(version,data,snapshot_hash,actor,reason,created_at) VALUES(?,?,?,?,?,?)", (version + 1, _json(data), digest(data), self.actor, reason, self._now()))
        return self.user_organization()

    def user_organization_history(self):
        return [self._registration(row) for row in self.db.execute("SELECT * FROM user_organization_versions ORDER BY version DESC")]
