"""Ponta a ponta com dados gerados: navegador → APIs → SQLite → arquivos.
Executa portal autenticado e interface local sem rede externa. Nenhum dado real.
"""

import hashlib
import json
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from src.persistence import AccountingStore
from src.local_app import LocalServer
from src.server.runtime import PortalServer
from test_persistence import fake_accounts, BUYER
from test_product_catalog import product_xml
from test_batch_import import zip_bytes
from playwright.sync_api import sync_playwright, expect


def run(mode):
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "synthetic.sqlite3"
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        server = (
            PortalServer(path, port) if mode == "portal" else LocalServer(path, port)
        )
        if mode == "portal":
            identity = server.app.state.identity
            identity.setup(
                {
                    "token": identity.setup_secret,
                    "name": "Operador sintético",
                    "email": "integrated@example.test",
                    "password": "synthetic-integrated-password",
                },
                "local",
            )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        if mode == "portal":
            deadline = time.monotonic() + 15
            while not server.server.started:
                if time.monotonic() > deadline:
                    raise RuntimeError("Servidor não iniciou")
                time.sleep(0.05)
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    executable_path=(
                        None
                        if Path(p.chromium.executable_path).exists()
                        else shutil.which("chromium")
                    ),
                    headless=True,
                    args=["--no-sandbox"],
                )
                page = browser.new_page(
                    viewport={"width": 1440, "height": 1000}, accept_downloads=True
                )
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{port}")
                labels = {
                    "setup": "Competências",
                    "chart": "Planos e mapeamentos",
                    "imports": "Documentos",
                    "fiscal": "Lançamento fiscal",
                    "reconciliation": "Conciliação",
                    "accounting": "Escrituração",
                    "finance": "Financeiro",
                    "books": "Livros e exportações",
                }
                if mode == "portal":
                    page.get_by_label("E-mail", exact=True).fill(
                        "integrated@example.test"
                    )
                    page.get_by_label("Senha", exact=True).fill(
                        "synthetic-integrated-password"
                    )
                    page.get_by_role("button", name="Entrar no ambiente").click()
                    page.get_by_role("link", name="Competências", exact=True).click()
                    frame = page.frame_locator("#workspace-frame")
                else:
                    frame = page

                def idle():
                    expect(frame.locator("main")).to_have_attribute(
                        "aria-busy", "false"
                    )

                def nav(panel):
                    if mode == "portal":
                        page.get_by_role(
                            "link", name=labels[panel], exact=True
                        ).first.click()
                    else:
                        frame.locator(".tab[data-panel=" + panel + "]").click()
                    expect(frame.locator("#" + panel)).to_be_visible()
                    idle()

                def submit(form, allow_partial=False):
                    invalid = form.locator(
                        "input:invalid,select:invalid,textarea:invalid"
                    ).evaluate_all(
                        "nodes => nodes.map(n => ({name:n.name,field:n.dataset.key || n.dataset.field,value:n.value,message:n.validationMessage}))"
                    )
                    assert not invalid, f"Formulário incompleto: {invalid}"
                    form.locator("button[type=submit]").click()
                    idle()
                    status = frame.locator("#status")
                    if status.is_visible() and not allow_partial:
                        assert "error" not in (
                            status.get_attribute("class") or ""
                        ), status.inner_text()

                nav("setup")
                company = frame.locator("#company-form")
                for key, value in [
                    ("name", "Empresa inteiramente sintética"),
                    ("prosoft_company_code", "TEST"),
                    ("prosoft_plan_code", "TEST"),
                    ("cnpj", BUYER),
                ]:
                    company.locator("[name=" + key + "]").fill(value)
                submit(company)
                expect(frame.locator("#company")).to_have_value("1")
                period = frame.locator("#period-form")
                period.locator("[name=reference_competence]").fill("2026-08")
                period.locator("[name=processing_competence]").fill("2026-09")
                submit(period)
                expect(frame.locator("#period")).to_have_value("1")
                nav("chart")
                plan = frame.locator("#plan-form")
                plan.locator("[name=label]").fill("Plano sintético")
                plan.locator("[name=accounts]").fill(json.dumps(fake_accounts()))
                submit(plan)
                for source, target in [("CAIXA", "1.1.1"), ("FORNECEDOR", "2.1")]:
                    form = frame.locator("#mapping-form")
                    form.locator("[name=source_account]").fill(source)
                    form.locator("[name=target_code]").fill(target)
                    form.locator("[name=valid_from]").fill("2026-09")
                    form.locator("[name=state]").select_option("aprovado")
                    form.locator("[name=reason]").fill("Mapeamento sintético conferido")
                    submit(form)
                nav("imports")
                packed = zip_bytes([("pasta/nfe-sintetica.xml", product_xml())])
                frame.locator("#upload-file").set_input_files(
                    [
                        {
                            "name": "fontes-sinteticas.zip",
                            "mimeType": "application/zip",
                            "buffer": packed,
                        },
                        {
                            "name": "invalido.xml",
                            "mimeType": "text/xml",
                            "buffer": b"<broken",
                        },
                    ]
                )
                submit(frame.locator("#file-form"), allow_partial=True)
                expect(frame.locator("#status")).to_contain_text(
                    "1 entrada(s) rejeitada(s)"
                )
                expect(frame.locator("#metric-documents")).to_have_text("1")
                expect(frame.locator("#products-list")).to_contain_text(
                    "Produto inteiramente fictício"
                )
                frame.locator("#import-batches-list > details > summary").first.click()
                with page.expect_download() as info:
                    frame.locator("#import-batches-list button").first.click()
                assert Path(info.value.path()).read_bytes() == packed
                expect(frame.locator("#import-batches-list")).to_contain_text(
                    "invalido.xml"
                )
                nav("fiscal")
                frame.locator("#fiscal-source").select_option("1")
                frame.locator("#fiscal-prepare").click()
                fiscal = frame.locator("#fiscal-form")
                expect(fiscal.locator("[name=number]")).to_have_value("1")
                fiscal.locator("[name=posting_date]").fill("2026-09-15")
                fiscal.locator("#fiscal-reason").fill("Fonte sintética conferida")
                submit(fiscal)
                review = frame.locator("#fiscal-entries form").first
                review.locator("[name=reason]").fill("Revisão sintética")
                review.locator("[type=checkbox]").check()
                submit(review)
                expect(frame.locator("#fiscal-entries")).to_contain_text("revisado")
                nav("reconciliation")
                review = frame.locator("#reconciliation-list form").last
                review.locator("select[name=chosen_observation_id]").select_option(
                    index=1
                )
                review.locator("[name=reason]").fill("Fonte sintética conferida")
                review.locator("[type=checkbox]").check()
                submit(review)
                nav("accounting")
                form = frame.locator("#accounting-form")
                form.locator("[name=plan_id]").select_option("1")
                for index, (side, mapping) in enumerate([("D", "1"), ("C", "2")]):
                    line = form.locator(".posting-line").nth(index)
                    line.locator("[data-field=document_id]").select_option("1")
                    line.locator("[data-field=group]").fill("Documento sintético")
                    line.locator("[data-field=date]").fill("2026-09-15")
                    line.locator("[data-field=side]").select_option(side)
                    line.locator("[data-field=amount]").fill("100,30")
                    line.locator("[data-field=mapping_id]").select_option(mapping)
                    line.locator("[data-field=memo]").fill(
                        "Registro sintético documental"
                    )
                form.locator("[name=reason]").fill("Partidas sintéticas conferidas")
                submit(form)
                for state in ["revisado", "fechado"]:
                    review = frame.locator("#accounting-list form").first
                    review.locator("[name=reason]").fill("Revisão sintética")
                    review.locator("[type=checkbox]").check()
                    submit(review)
                    expect(frame.locator("#accounting-list h3")).to_contain_text(state)
                manual = frame.locator("#manual-form")
                held = []
                pattern = "**/api/accounts?*"
                page.route(pattern, lambda route: held.append(route))
                manual.locator("[name=plan_id]").select_option("1")
                expect(frame.locator("main")).to_have_attribute("aria-busy", "true")
                line = manual.locator(".manual-line").first
                line.locator("[data-key=memo]").fill(
                    "Histórico durante consulta de contas"
                )
                line.locator("[data-key=amount]").fill("0,30")
                line.locator("[data-key=date]").fill("2026-09-16")
                assert len(held) == 1
                held[0].continue_()
                page.unroute(pattern)
                idle()
                expect(line.locator("[data-key=memo]")).to_have_value(
                    "Histórico durante consulta de contas"
                )
                expect(line.locator("[data-key=amount]")).to_have_value("0,30")
                expect(line.locator("[data-key=date]")).to_have_value("2026-09-16")
                manual.locator("[name=reference]").fill("Lançamento livre sintético")
                manual.locator("[name=reason]").fill("Registro manual sintético")
                for index, (side, account) in enumerate([("D", "3"), ("C", "5")]):
                    line = manual.locator(".manual-line").nth(index)
                    for key, value in [
                        ("date", "2026-09-16"),
                        ("amount", "0,30"),
                        ("memo", "Registro manual sintético"),
                    ]:
                        line.locator("[data-key=" + key + "]").fill(value)
                    line.locator("[data-key=side]").select_option(side)
                    line.locator("[data-key=account_id]").select_option(account)
                nav("finance")
                nav("accounting")
                expect(manual.locator("[name=reference]")).to_have_value(
                    "Lançamento livre sintético"
                )
                submit(manual)
                frame.get_by_role(
                    "button", name="Editar lançamento manual", exact=True
                ).click()
                expect(manual.locator("[name=expected_version]")).to_have_value("1")
                manual.locator("[name=reference]").fill(
                    "Lançamento livre sintético corrigido"
                )
                manual.locator("[name=reason]").fill("Correção sintética explícita")
                for line in [manual.locator(".manual-line").nth(i) for i in range(2)]:
                    line.locator("[data-key=amount]").fill("0,40")
                submit(manual)
                expect(frame.locator("#manual-list h3")).to_contain_text("v2")
                for state in ["revisado", "fechado"]:
                    review = frame.locator("#manual-list form").first
                    review.locator("[name=reason]").fill("Conferência manual sintética")
                    review.locator("[type=checkbox]").check()
                    submit(review)
                    expect(frame.locator("#manual-list h3")).to_contain_text(state)
                nav("books")
                frame.locator("#books-plan").select_option("1")
                submit(frame.locator("#books-form"))
                expect(frame.locator("#books-summary")).to_contain_text(
                    "Débitos 100.70 · Créditos 100.70 · 2 origem(ns)"
                )
                export = frame.locator("#books-export-form")
                export.locator("[name=reason]").fill("Exportação sintética")
                submit(export)
                with page.expect_download() as info:
                    frame.get_by_role(
                        "button", name="Baixar books.json", exact=True
                    ).click()
                downloaded = Path(info.value.path()).read_bytes()
                books = json.loads(downloaded)
                assert books["totals"]["debit"] == "100.70"
                assert len(books["diary"]) == 4
                with AccountingStore(path) as store:
                    preserved = store.list_book_exports(1)[0]
                    artifact = next(
                        row
                        for row in preserved["artifacts"]
                        if row["name"] == "books.json"
                    )
                    assert hashlib.sha256(downloaded).hexdigest() == artifact["sha256"]
                nav("accounting")
                reversal = frame.locator("#manual-list form").first
                reversal.locator("[name=date]").fill("2026-09-18")
                reversal.locator("[name=reason]").fill(
                    "Estorno manual sintético vinculado"
                )
                reversal.locator("[type=checkbox]").check()
                submit(reversal)
                for state in ["revisado", "fechado"]:
                    review = (
                        frame.locator("#manual-list article")
                        .first.locator("form")
                        .first
                    )
                    review.locator("[name=reason]").fill(
                        "Conferência do estorno sintético"
                    )
                    review.locator("[type=checkbox]").check()
                    submit(review)
                    expect(frame.locator("#manual-list h3").first).to_contain_text(
                        state
                    )
                nav("finance")
                form = frame.locator("#finance-form")
                for key, value in [
                    ("reference", "Título sintético"),
                    ("counterparty", "Fornecedor sintético"),
                    ("due_date", "2026-09-20"),
                    ("amount", "100,30"),
                    ("reason", "Compromisso sintético"),
                ]:
                    form.locator("[name=" + key + "]").fill(value)
                submit(form)
                card = frame.locator('#finance-list [data-title="1"]')
                expect(card).to_contain_text("saldo 100.30")
                for amount, balance in [("40,10", "60.20"), ("60,20", "0.00")]:
                    settlement = card.locator("form").first
                    for key, value in [
                        ("amount", amount),
                        ("paid_date", "2026-09-20"),
                        ("reference", "Baixa sintética"),
                        ("reason", "Conferência sintética"),
                    ]:
                        settlement.locator("[name=" + key + "]").fill(value)
                    submit(settlement)
                    expect(card).to_contain_text("saldo " + balance)
                reversal = card.locator("form").first
                reversal.locator("[name=reason]").fill("Estorno sintético")
                submit(reversal)
                expect(card).to_contain_text("saldo 40.10")
                for key, value in [
                    ("reference", "Título incorreto sintético"),
                    ("counterparty", "Fornecedor sintético"),
                    ("due_date", "2026-09-20"),
                    ("amount", "5,00"),
                    ("reason", "Inclusão sintética"),
                ]:
                    form.locator("[name=" + key + "]").fill(value)
                submit(form)
                canceled = frame.locator('#finance-list [data-title="2"]')
                cancellation = canceled.locator("form").last
                cancellation.locator("[name=reason]").fill(
                    "Cancelamento sintético explícito"
                )
                cancellation.locator("[type=checkbox]").check()
                submit(cancellation)
                expect(canceled).to_contain_text("cancelado")
                expect(canceled).to_contain_text("saldo 0.00")
                with page.expect_download() as info:
                    frame.locator("#finance-download").click()
                assert b"40.10" in Path(info.value.path()).read_bytes()
                for width in [1440, 768, 390, 320]:
                    page.set_viewport_size({"width": width, "height": 900})
                    assert page.evaluate(
                        "document.documentElement.scrollWidth<=innerWidth+1"
                    )
                    assert frame.locator("html").evaluate(
                        "(e)=>e.scrollWidth<=innerWidth+1"
                    )
                assert not errors, errors
                browser.close()
            with AccountingStore(path) as store:
                assert store.list_finance_titles(1)[0]["balance"] == "40.10"
                assert store.list_manual_journals(1)[0]["status"] == "fechado"
                assert store.list_fiscal_entries(1)[0]["current"]["state"] == "revisado"
                assert len(store.accounting_books(1, 1, 1)["diary"]) == 6
                assert store.accounting_books(1, 1, 1)["totals"]["debit"] == "101.10"
                assert (
                    store.read_book_artifact(1, preserved["id"], "books.json")[
                        "content"
                    ]
                    == downloaded
                )
            print(
                "PASS "
                + mode
                + ": UI company/period/chart/mappings → mixed ZIP/XML batch/original/catalog → fiscal review → document review → documentary/manual edit/close/reversal → books JSON/hash/download → partial/full settlement/reversal/cancellation/CSV; persisted SQLite; responsive; no JS errors",
                flush=True,
            )
        finally:
            server.shutdown()
            thread.join(10)
            server.server_close()


if __name__ == "__main__":
    run("portal")
    run("local")
