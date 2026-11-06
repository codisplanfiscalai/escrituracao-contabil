"""Private, single-user HTTP interface. Run with ``python -m src.local_app``.

This deliberately is not an authenticated multi-user service. Never expose it
through a proxy, public tunnel, port forwarding, or a non-loopback listener.
"""

from __future__ import annotations

import argparse
import base64
import binascii
from contextlib import contextmanager
import hmac
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import sqlite3
from urllib.parse import parse_qs, urlsplit
from .work_api import WORK_ROUTES, RETIRED_WRITES, dispatch_work
from .finance import FINANCE_ROUTES, dispatch_finance
from .accounting_api import ACCOUNTING_ROUTES, dispatch_accounting

MAX_BODY = 15 * 1024 * 1024
WEB_ROOT = Path(__file__).resolve().parent / "web"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS = {
    "/workbench.js": ("workbench.js", "text/javascript; charset=utf-8"),
    "/workbench_render.js": ("workbench_render.js", "text/javascript; charset=utf-8"),
    "/workbench.css": ("workbench.css", "text/css; charset=utf-8"),
    "/assets/symbol.svg": ("assets/symbol.svg", "image/svg+xml"),
    "/assets/icon.svg": ("assets/icon.svg", "image/svg+xml"),
    "/favicon.ico": ("assets/icon.ico", "image/x-icon"),
}
ASSETS["/portal/vendor/vue.js"] = ("../portal/vendor/vue.js", "text/javascript; charset=utf-8")
ASSETS.update(
    {
        f"/assets/icon-{size}.png": (f"assets/icon-{size}.png", "image/png")
        for size in (16, 24, 32, 48, 64, 128, 256, 512)
    }
)


class APIError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


@contextmanager
def open_store(database):
    from .persistence import AccountingStore

    store = AccountingStore(database, actor="operador-local")
    try:
        yield store
    finally:
        store.close()


def _required(data, name):
    if name not in data or data[name] is None or data[name] == "":
        raise APIError(f"Informe o campo {name}.")
    return data[name]


def _identifier(value, name):
    # The persistence layer owns identifiers. Preserve strings, reject containers.
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, str))
        or str(value).strip() == ""
    ):
        raise APIError(f"Identificador inválido: {name}.")
    return value


def dispatch(store, method, route, data):
    """Small explicit API; no method names or paths are chosen by the client."""
    if method == "POST" and route in RETIRED_WRITES:
        raise APIError(
            "Gravação retirada: use a ficha de operação da escrituração. Histórico anterior permanece consultável.",
            410,
        )
    if route in WORK_ROUTES:
        return dispatch_work(store, method, route, data)
    if route in FINANCE_ROUTES:
        return dispatch_finance(store, method, route, data)
    if route in ACCOUNTING_ROUTES:
        return dispatch_accounting(store, method, route, data)
    company = None
    if route != "companies":
        company = _identifier(_required(data, "company_id"), "company_id")
    if method == "GET":
        if route == "company-profile":
            return store.client_profile(company)
        if route == "company-profile-history":
            return store.client_profile_history(company)
        if route == "products":
            return store.list_products(company)
        if route == "import-batches":
            return store.list_import_batches(company, data.get("period_id") or None)
        if route == "import-original":
            return store.read_import_original(company, _required(data, "item_id"))
        if route == "participants":
            return store.list_participants(company)
        if route == "fiscal-workspaces":
            return store.list_fiscal_workspaces(company, _required(data, "period_id"))
        if route == "fiscal-entries":
            return store.list_fiscal_entries(company, data.get("period_id") or None)
        if route == "fiscal-seed":
            return store.fiscal_seed(
                company, _required(data, "period_id"), _required(data, "document_id")
            )
        if route == "fiscal-period":
            return store.fiscal_period_status(company, _required(data, "period_id"))
        if route == "billing-associations":
            return store.list_billing_associations(
                company, data.get("document_id") or None
            )
        if route == "accounting-evidence":
            return store.list_evidence_exports(company, data.get("batch_id") or None)
        if route == "accounting-evidence-file":
            return store.read_evidence_artifact(
                company, _required(data, "export_id"), _required(data, "name")
            )
        if route == "document-reviews":
            return store.list_document_reviews(company, data.get("document_id") or None)
        if route == "accounting-batches":
            return store.list_accounting_batches(company)
        if route == "companies":
            return store.list_companies()
        if route == "periods":
            return store.list_periods(company)
        if route == "plans":
            return store.list_plans(company)
        if route == "accounts":
            return store.list_accounts(
                company, _identifier(_required(data, "plan_id"), "plan_id")
            )
        if route == "mappings":
            return store.list_mappings(company)
        if route == "files":
            return store.list_files(company)
        if route == "file-preview":
            return store.deletion_preview(
                company, _identifier(_required(data, "file_id"), "file_id")
            )
        if route in {"reconciliation", "observations"}:
            period = data.get("period_id")
            period = None if period in (None, "") else _identifier(period, "period_id")
            return (
                store.list_reconciliation(company, period)
                if route == "reconciliation"
                else store.list_observations(company, period)
            )
        if route == "documents":
            period = data.get("period_id")
            return store.list_documents(
                company,
                None if period in (None, "") else _identifier(period, "period_id"),
            )
        if route == "audit":
            return store.list_audit(company)
    if method == "POST":
        if route == "company-profile":
            return store.save_client_profile(company, _required(data, "data"), data.get("version"), _required(data, "reason"))
        if route == "product-review":
            return store.review_product(
                company,
                _required(data, "product_id"),
                _required(data, "version"),
                _required(data, "observation_id"),
                _required(data, "reason"),
            )

        if route == "participants":
            return store.save_participant(
                company,
                _required(data, "identity"),
                _required(data, "name"),
                _required(data, "role"),
                _required(data, "reason"),
            )
        if route == "participant-review":
            return store.review_participant(
                company,
                _required(data, "participant_id"),
                _required(data, "version"),
                _required(data, "observation_id"),
                _required(data, "reason"),
            )
        if route == "fiscal-workspaces":
            return store.save_fiscal_workspace(
                company,
                _required(data, "period_id"),
                _required(data, "title"),
                data.get("data", {}),
                _required(data, "request_key"),
                data.get("workspace_id"),
                data.get("version", 0),
                data.get("closed", False),
            )
        if route == "fiscal-entries":
            return store.save_fiscal_entry(
                company,
                _required(data, "period_id"),
                _required(data, "data"),
                _required(data, "reason"),
                _required(data, "request_key"),
                data.get("expected_version", 0),
                data.get("entry_id") or None,
                data.get("document_id") or None,
                data.get("expected_source_hash"),
                data.get("as_proposal", False),
            )
        if route == "fiscal-review":
            return store.review_fiscal_entry(
                company,
                _required(data, "entry_id"),
                _required(data, "snapshot_hash"),
                _required(data, "reason"),
                data.get("acknowledged", False),
            )
        if route == "fiscal-period":
            return store.change_fiscal_period(
                company,
                _required(data, "period_id"),
                _required(data, "target"),
                _required(data, "token"),
                _required(data, "reason"),
                data.get("confirmed", False),
                data.get("reference", ""),
            )
        if route in {"billing-association-preview", "billing-associations"}:
            args = [
                company,
                _required(data, "document_id"),
                _required(data, "period_id"),
                _required(data, "file_id"),
                _required(data, "invoice_id"),
                _required(data, "installment_links"),
            ]
            if route == "billing-association-preview":
                return store.preview_billing_association(*args)
            return store.save_billing_association(
                *args,
                _required(data, "expected_fingerprint"),
                _required(data, "reason"),
                data.get("confirmed", False),
            )
        if route == "accounting-evidence":
            return store.create_evidence_export(
                company,
                _required(data, "batch_id"),
                _required(data, "snapshot_hash"),
                _required(data, "reason"),
            )
        if route == "document-reviews":
            return store.save_document_review(
                company,
                _required(data, "document_id"),
                _required(data, "period_id"),
                _required(data, "chosen_observation_id"),
                _required(data, "expected_fingerprint"),
                _required(data, "reason"),
            )
        if route == "accounting-batches":
            return store.create_accounting_batch(
                company,
                _required(data, "period_id"),
                _required(data, "plan_id"),
                _required(data, "request_key"),
                _required(data, "entries"),
                _required(data, "reason"),
                data.get("previous_batch_id") or None,
            )
        if route in {"accounting-review", "accounting-close"}:
            method_call = (
                store.review_accounting_batch
                if route == "accounting-review"
                else store.close_accounting_batch
            )
            return method_call(
                company,
                _required(data, "batch_id"),
                _required(data, "snapshot_hash"),
                _required(data, "reason"),
            )
        if route == "file-analysis":
            return store.index_file(
                company,
                _identifier(_required(data, "file_id"), "file_id"),
                _required(data, "profile"),
            )
        if route == "file-removal":
            return store.delete_file(
                company,
                _identifier(_required(data, "file_id"), "file_id"),
                _required(data, "reason"),
                confirmed=data.get("confirmed"),
                preview_token=_required(data, "preview_token"),
            )
        if route == "companies":
            return store.create_company(
                _required(data, "name"),
                data.get("prosoft_company_code", ""),
                data.get("prosoft_plan_code", ""),
                cnpj=data.get("cnpj", ""),
            )
        if route == "periods":
            return store.create_period(
                company,
                _required(data, "reference_competence"),
                _required(data, "processing_competence"),
            )
        if route == "plans":
            accounts = _required(data, "accounts")
            if not isinstance(accounts, list) or not all(
                isinstance(a, dict) for a in accounts
            ):
                raise APIError("accounts deve ser uma lista JSON de objetos.")
            return store.import_plan(company, _required(data, "label"), accounts)
        if route == "mappings":
            return store.save_mapping(
                company,
                _identifier(_required(data, "plan_id"), "plan_id"),
                _required(data, "source_account"),
                _required(data, "target_code"),
                _required(data, "valid_from"),
                valid_to=data.get("valid_to") or None,
                state=data.get("state", "rascunho"),
                reason=data.get("reason", ""),
            )
        if route == "import-batches":
            inputs = _required(data, "inputs")
            if not isinstance(inputs, list) or not 1 <= len(inputs) <= 500:
                raise APIError("Envie de 1 a 500 arquivos por lote.")
            decoded = []
            for item in inputs:
                if not isinstance(item, dict) or not isinstance(
                    item.get("content_base64"), str
                ):
                    raise APIError("Cada entrada exige filename e content_base64.")
                try:
                    content = base64.b64decode(item["content_base64"], validate=True)
                except (ValueError, binascii.Error):
                    raise APIError("Conteúdo base64 inválido no lote.") from None
                decoded.append(
                    {
                        "filename": item.get("filename"),
                        "kind": item.get("kind"),
                        "content": content,
                    }
                )
            return store.import_batch(
                company,
                _identifier(_required(data, "period_id"), "period_id"),
                decoded,
                _required(data, "request_key"),
                sped_profile=data.get("sped_profile") or None,
            )
        if route == "files":
            encoded = _required(data, "content_base64")
            if not isinstance(encoded, str):
                raise APIError("content_base64 deve ser texto em base64.")
            try:
                content = base64.b64decode(encoded, validate=True)
            except (ValueError, binascii.Error):
                raise APIError("Conteúdo base64 inválido.") from None
            filename = _required(data, "filename")
            if (
                not isinstance(filename, str)
                or any(c in filename for c in ("/", "\\", "\x00"))
                or filename in (".", "..")
            ):
                raise APIError("Envie somente o nome do arquivo, sem caminho.")
            kind = _required(data, "kind")
            if kind not in ("XML", "SPED"):
                raise APIError("kind deve ser XML ou SPED.")
            return store.import_file(
                company,
                _identifier(_required(data, "period_id"), "period_id"),
                filename,
                content,
                kind,
                sped_profile=data.get("sped_profile") or None,
            )
    raise APIError("Rota ou método não disponível.", 404)


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, database, port=8765):
        self.database = str(database)
        self.token = secrets.token_urlsafe(32)
        super().__init__(("127.0.0.1", port), LocalHandler)


class LocalHandler(BaseHTTPRequestHandler):
    server_version = "EscrituraLocal/0.2"
    sys_version = ""
    protocol_version = "HTTP/1.0"

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, format, *args):
        # Requests may contain private company identifiers; do not log their URLs.
        pass

    def _send(
        self,
        status,
        content,
        content_type="application/json; charset=utf-8",
        attachment=None,
    ):
        if not isinstance(content, bytes):
            content = json.dumps(content, ensure_ascii=False, allow_nan=False).encode(
                "utf-8"
            )
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        if attachment is not None:
            self.send_header(
                "Content-Disposition", f'attachment; filename="{attachment}"'
            )
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
        )
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(content)

    def send_error(self, code, message=None, explain=None):
        self._send(code, {"error": "Requisição HTTP não permitida."})

    def _security(self, require_token=False):
        port = self.server.server_port
        allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        hosts = self.headers.get_all("Host", [])
        if len(hosts) != 1 or hosts[0] not in allowed_hosts:
            raise APIError(
                "Host não permitido. Abra o endereço local informado na inicialização.",
                403,
            )
        origins = self.headers.get_all("Origin", [])
        if len(origins) > 1 or (origins and origins[0] != f"http://{hosts[0]}"):
            raise APIError("Origem não permitida.", 403)
        if self.command == "POST" and not origins:
            raise APIError("Cabeçalho Origin obrigatório.", 403)
        if self.headers.get("Sec-Fetch-Site", "") not in ("", "same-origin", "none"):
            raise APIError("Requisição de outro site não permitida.", 403)
        if require_token:
            tokens = self.headers.get_all("X-Local-Token", [])
            if len(tokens) != 1 or not hmac.compare_digest(
                tokens[0], self.server.token
            ):
                raise APIError("Sessão local inválida. Recarregue a página.", 403)

    def _body(self):
        if self.headers.get("Transfer-Encoding") is not None:
            raise APIError("Transfer-Encoding não é aceito.")
        lengths = self.headers.get_all("Content-Length", [])
        if len(lengths) != 1 or not lengths[0].isdigit():
            raise APIError("Content-Length válido é obrigatório.", 411)
        length = int(lengths[0])
        if length > MAX_BODY:
            raise APIError("O envio excede o limite de 15 MiB (JSON com base64).", 413)
        if self.headers.get_content_type() != "application/json":
            raise APIError("Use Content-Type application/json.", 415)
        raw = self.rfile.read(length)
        if len(raw) != length:
            raise APIError("Envio incompleto.")
        try:
            data = json.loads(
                raw.decode("utf-8"),
                parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
            )
        except (UnicodeError, ValueError, RecursionError):
            raise APIError("JSON inválido.") from None
        if not isinstance(data, dict):
            raise APIError("O corpo JSON deve ser um objeto.")
        return data

    def _handle(self):
        try:
            parts = urlsplit(self.path)
            self._security(parts.path.startswith("/api/"))
            if parts.scheme or parts.netloc or parts.fragment:
                raise APIError("URL inválida.")
            if self.command == "GET" and parts.path in ("/", "/index.html"):
                html = (
                    (WEB_ROOT / "index.html")
                    .read_text(encoding="utf-8")
                    .replace("__LOCAL_TOKEN__", self.server.token)
                )
                self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
                return
            if self.command == "GET" and parts.path in ASSETS:
                filename, content_type = ASSETS[parts.path]
                self._send(200, (WEB_ROOT / filename).read_bytes(), content_type)
                return
            routes = {
                "participants",
                "participant-review",
                "fiscal-workspaces",
                "fiscal-entries",
                "fiscal-seed",
                "fiscal-period",
                "fiscal-review",
                "products",
                "product-review",
                "import-batches",
                "import-original",
                "billing-association-preview",
                "billing-associations",
                "companies",
                "periods",
                "plans",
                "accounts",
                "mappings",
                "files",
                "documents",
                "audit",
                "file-preview",
                "file-removal",
                "file-analysis",
                "reconciliation",
                "observations",
                "document-reviews",
                "accounting-batches",
                "accounting-review",
                "accounting-close",
                "accounting-evidence",
                "accounting-evidence-file",
            }
            route = parts.path.removeprefix("/api/")
            routes.update(ACCOUNTING_ROUTES | FINANCE_ROUTES | WORK_ROUTES)
            if not parts.path.startswith("/api/") or route not in routes:
                raise APIError("Página não encontrada.", 404)
            if self.command == "POST":
                if parts.query:
                    raise APIError("Não envie parâmetros na URL de gravação.")
                data = self._body()
            else:
                parsed = parse_qs(
                    parts.query, keep_blank_values=True, max_num_fields=12
                )
                if any(len(values) != 1 for values in parsed.values()):
                    raise APIError("Parâmetros repetidos não são aceitos.")
                data = {key: values[0] for key, values in parsed.items()}
            with open_store(self.server.database) as store:
                result = dispatch(store, self.command, route, data)
            if (
                route
                in {
                    "accounting-evidence-file",
                    "accounting-book-file",
                    "finance-file",
                    "import-original",
                    "work-export-file",
                    "source-original",
                }
                and self.command == "GET"
            ):
                # Core accepts only its fixed artifact names, never a client path.
                self._send(
                    200,
                    result["content"],
                    result["media_type"],
                    attachment=result["name"],
                )
            else:
                self._send(200 if self.command == "GET" else 201, {"data": result})
        except APIError as exc:
            self._send(exc.status, {"error": str(exc)})
        except (ValueError, TypeError) as exc:
            # Core validation errors are user-readable, but never leak path details.
            message = str(exc)
            if (
                self.server.database in message
                or "Traceback" in message
                or len(message) > 500
            ):
                message = "Dados inválidos. Confira os campos informados."
            self._send(400, {"error": message or "Dados inválidos."})
        except (sqlite3.IntegrityError, KeyError):
            self._send(
                409,
                {
                    "error": "Registro inexistente, duplicado ou incompatível com a empresa selecionada."
                },
            )
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass
        except Exception:
            self._send(
                500,
                {
                    "error": "Não foi possível concluir a operação local. Confira os dados e tente novamente."
                },
            )

    do_GET = _handle
    do_POST = _handle


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Escritura: aplicação contábil local e monousuário. Nunca exponha em rede."
    )
    parser.add_argument(
        "--database",
        default=str(
            Path.home() / ".local" / "share" / "prosoft-local" / "accounting.sqlite3"
        ),
        help="SQLite privado fora da pasta do projeto",
    )
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("a porta deve estar entre 1 e 65535")
    database = Path(args.database).expanduser().resolve()
    if database == PROJECT_ROOT or PROJECT_ROOT in database.parents:
        parser.error(
            "guarde o SQLite fora da pasta do projeto para não versionar dados privados"
        )
    try:
        database.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with open_store(str(database)):
            pass
        server = LocalServer(database, args.port)
    except Exception:
        parser.exit(
            1,
            "Não foi possível abrir o SQLite privado ou a porta local. Confira o caminho, as permissões e a porta.\n",
        )
    print(
        f"Protótipo local monousuário: http://127.0.0.1:{server.server_port}",
        flush=True,
    )
    print(
        "Sem autenticação multiusuário, apuração CBS/IBS ou exportação Prosoft homologada. Ctrl+C para encerrar.",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
