"use strict";
// Shared by local Windows workspace and authenticated server. Drafts remain scoped.
window.IntegratedWorkspace = (() => {
  let scope = "",
    drafts = {},
    accounts = [],
    books = null,
    version = 0,
    manualGeneration = 0;
  const storage =
    "escritura:integrated-drafts:v1:" +
    (window.frameElement?.dataset.owner || "local");
  const defaultLines = () =>
    ["D", "C"].map((side) => ({
      date: "",
      group: "1",
      side,
      amount: "",
      account_id: "",
      memo: "",
    }));
  const blank = () => ({
    plan_id: "",
    reference: "",
    reason: "",
    request_key: crypto.randomUUID(),
    journal_id: "",
    expected_version: "0",
    lines: defaultLines(),
  });
  function save() {
    if (!scope) return;
    const f = $("#manual-form"),
      finance = $("#finance-form");
    drafts[scope] = {
      manual: {
        ...formObject(f),
        lines: [...document.querySelectorAll(".manual-line")].map((row) =>
          Object.fromEntries(
            [...row.querySelectorAll("[data-key]")].map((c) => [
              c.dataset.key,
              c.value,
            ]),
          ),
        ),
      },
      finance: formObject(finance),
    };
    try {
      sessionStorage.setItem(storage, JSON.stringify(drafts));
      $("#manual-draft-state").textContent =
        "Rascunho manual recuperável nesta sessão.";
    } catch {
      throw Error("Não foi possível preservar o rascunho manual.");
    }
  }
  function clearDrafts() {
    drafts = {};
    scope = "";
    sessionStorage.removeItem(storage);
  }
  function lines(rows) {
    const area = $("#manual-lines");
    area.replaceChildren();
    rows.forEach((row, index) => {
      const card = element("div");
      card.className = "manual-line fiscal-grid";
      for (const [key, label] of Object.entries({
        date: "Data contábil",
        group: "Grupo",
        side: "D/C",
        amount: "Valor da partida",
        account_id: "Conta analítica",
        memo: "Histórico manual",
      })) {
        const wrap = element("label", label),
          c = element(
            key === "side" || key === "account_id" ? "select" : "input",
          );
        c.dataset.key = key;
        c.required = true;
        c.setAttribute("aria-label", label + " " + (index + 1));
        if (key === "date") c.type = "date";
        if (key === "amount") c.inputMode = "decimal";
        if (key === "side") {
          option(c, "D", "Débito");
          option(c, "C", "Crédito");
        }
        if (key === "account_id") {
          option(c, "", "Selecione a conta");
          accounts
            .filter((a) => a.kind === "analitica")
            .forEach((a) => option(c, a.id, a.code + " · " + a.description));
        }
        c.value = row[key] || "";
        wrap.append(c);
        card.append(wrap);
      }
      const remove = element("button", "Remover partida manual");
      remove.type = "button";
      remove.onclick = () => {
        card.remove();
        save();
      };
      card.append(remove);
      area.append(card);
    });
  }
  async function restoreManual(value) {
    const request = ++manualGeneration,
      company = companyId();
    const f = $("#manual-form");
    for (const key of [
      "plan_id",
      "reference",
      "reason",
      "request_key",
      "journal_id",
      "expected_version",
    ])
      f.elements[key].value =
        value[key] || (key === "expected_version" ? "0" : "");
    const resolvedAccounts = value.plan_id
      ? await api("accounts", {
          company_id: companyId(),
          plan_id: value.plan_id,
        })
      : [];
    if (request !== manualGeneration || company !== companyId()) return;
    accounts = resolvedAccounts;
    lines(value.lines || defaultLines());
  }
  async function download(route, query, name, expected) {
    const response = await fetch(
      "/api/" + route + "?" + new URLSearchParams(query),
      { cache: "no-store", headers: { "X-Local-Token": token } },
    );
    if (!response.ok) {
      let body = await response.json();
      throw Error(body.error || "Falha no download");
    }
    const bytes = await response.arrayBuffer();
    if (expected) {
      const hash = Array.from(
        new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
        (value) => value.toString(16).padStart(2, "0"),
      ).join("");
      if (hash !== expected.sha256 || bytes.byteLength !== expected.size)
        throw Error("Arquivo recebido diverge do hash e tamanho preservados.");
    }
    const url = URL.createObjectURL(
        new Blob([bytes], { type: response.headers.get("Content-Type") }),
      ),
      a = element("a");
    a.href = url;
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function actionButton(card, label, handler) {
    const button = element("button", label);
    button.type = "button";
    button.onclick = async () => {
      if (busy) return;
      setBusy(1);
      try {
        await handler();
      } catch (e) {
        notice(e.message, true);
      } finally {
        setBusy(-1);
      }
    };
    card.append(button);
  }
  function renderManual(rows) {
    const area = $("#manual-list");
    area.replaceChildren();
    rows.forEach((row) => {
      const card = element("article");
      card.className = "card";
      card.dataset.journal = row.journal_id;
      card.append(
        element(
          "h3",
          `Manual #${row.journal_id} · v${row.version} · ${row.status}`,
        ),
        element("p", row.snapshot.reference),
      );
      const details = element("details");
      details.append(
        element("summary", "Conferir snapshot manual"),
        element("pre", JSON.stringify(row.snapshot, null, 2)),
      );
      card.append(details);
      if (row.status !== "fechado" && row.reversal_of === null)
        actionButton(card, "Editar lançamento manual", async () => {
          await restoreManual({
            ...row.snapshot,
            plan_id: row.plan_id,
            journal_id: row.journal_id,
            expected_version: row.version,
            reason: "",
            request_key: crypto.randomUUID(),
            lines: row.snapshot.entries.map((line) => ({
              ...line,
              account_id: line.account.id,
            })),
          });
          save();
          $("#manual-form").scrollIntoView();
        });
      if (["previa", "revisado"].includes(row.status)) {
        const f = element("form");
        const reason = labeledControl(
            f,
            "Motivo da decisão manual",
            "input",
            "reason",
          ),
          check = confirmedControl(
            f,
            "Conferi as partidas desta versão manual.",
          );
        const b = element(
          "button",
          row.status === "previa" ? "Revisar manual" : "Fechar manual",
        );
        b.type = "submit";
        f.append(b);
        localAction(f, async () => {
          if (!check.checked) throw Error("Confira a versão.");
          await api(
            row.status === "previa" ? "manual-review" : "manual-close",
            {
              company_id: companyId(),
              journal_id: row.journal_id,
              snapshot_hash: row.snapshot_hash,
              reason: reason.value,
            },
            "POST",
          );
        });
        card.append(f);
      }
      if (row.status === "fechado" && row.reversal_of === null) {
        const f = element("form"),
          date = labeledControl(f, "Data do estorno manual", "input", "date"),
          reason = labeledControl(
            f,
            "Motivo do estorno manual",
            "input",
            "reason",
          );
        date.type = "date";
        const check = confirmedControl(
          f,
          "Criar estorno vinculado no período selecionado.",
        );
        const b = element("button", "Criar estorno manual");
        b.type = "submit";
        f.append(b);
        localAction(f, async () => {
          if (!check.checked) throw Error("Confirme o estorno.");
          await api(
            "manual-reversal",
            {
              company_id: companyId(),
              period_id: periodId(),
              journal_id: row.journal_id,
              date: date.value,
              reason: reason.value,
              snapshot_hash: row.snapshot_hash,
            },
            "POST",
          );
        });
        card.append(f);
      }
      area.append(card);
    });
  }
  function renderFinance(rows) {
    const area = $("#finance-list");
    area.replaceChildren();
    $("#finance-totals").textContent =
      rows.length +
      " título(s) neste recorte. Valores e saldos por título abaixo.";
    rows.forEach((row) => {
      const card = element("article");
      card.className = "card";
      card.dataset.title = row.id;
      card.append(
        element(
          "h3",
          `${row.direction === "pagar" ? "A pagar" : "A receber"} #${row.id} · ${row.reference}`,
        ),
        element(
          "p",
          `${row.counterparty} · vence ${row.due_date} · ${row.status} · valor ${row.amount} · baixado ${row.paid} · saldo ${row.balance}`,
        ),
      );
      if (row.balance !== "0.00") {
        const f = element("form"),
          value = labeledControl(f, "Valor da baixa", "input", "amount"),
          date = labeledControl(f, "Data da baixa", "input", "paid_date"),
          ref = labeledControl(f, "Referência da baixa", "input", "reference"),
          reason = labeledControl(f, "Motivo da baixa", "input", "reason");
        date.type = "date";
        value.inputMode = "decimal";
        const key = crypto.randomUUID(),
          button = element("button", "Registrar baixa");
        button.type = "submit";
        f.append(button);
        localAction(f, () =>
          api(
            "finance-settlements",
            {
              company_id: companyId(),
              title_id: row.id,
              amount: value.value.replace(",", "."),
              paid_date: date.value,
              reference: ref.value,
              reason: reason.value,
              request_key: key,
              snapshot_hash: row.snapshot_hash,
            },
            "POST",
          ),
        );
        card.append(f);
      }
      if (!row.canceled_at && row.paid === "0.00") {
        const form = element("form"),
          reason = labeledControl(
            form,
            "Motivo do cancelamento do título",
            "input",
            "reason",
          );
        const confirmed = confirmedControl(
          form,
          "Cancelar este título e preservar seu histórico.",
        );
        const button = element("button", "Cancelar título #" + row.id);
        button.type = "submit";
        form.append(button);
        localAction(form, () => {
          if (!confirmed.checked) throw Error("Confirme o cancelamento.");
          return api(
            "finance-cancel",
            {
              company_id: companyId(),
              title_id: row.id,
              snapshot_hash: row.snapshot_hash,
              reason: reason.value,
            },
            "POST",
          );
        });
        card.append(form);
      }
      if (row.canceled_at)
        card.append(element("p", "Cancelado: " + row.cancellation_reason));
      row.settlements.forEach((baixa) => {
        card.append(
          element(
            "p",
            `Baixa #${baixa.id} · ${baixa.paid_date} · ${baixa.amount} · ${baixa.reference}${baixa.reversed_at ? " · estornada: " + baixa.reversal_reason : ""}`,
          ),
        );
        if (!baixa.reversed_at) {
          const f = element("form"),
            reason = labeledControl(
              f,
              "Motivo do estorno da baixa",
              "input",
              "reason",
            ),
            button = element("button", "Estornar baixa #" + baixa.id);
          button.type = "submit";
          f.append(button);
          localAction(f, () =>
            api(
              "finance-reversal",
              {
                company_id: companyId(),
                title_id: row.id,
                settlement_id: baixa.id,
                snapshot_hash: row.snapshot_hash,
                reason: reason.value,
              },
              "POST",
            ),
          );
          card.append(f);
        }
      });
      area.append(card);
    });
  }
  function clearView() {
    books = null;
    renderManual([]);
    renderFinance([]);
    $("#books-export-form").hidden = true;
    $("#books-exports").replaceChildren();
    $("#books-summary").textContent = "";
    table("#books-preview", []);
  }
  async function load() {
    const v = ++version;
    clearView();
    scope = companyId() + ":" + periodId();
    books = null;
    $("#books-export-form").hidden = true;
    $("#books-summary").textContent = "";
    table("#books-preview", []);
    fillSelect(
      $("#manual-plan"),
      current.plans,
      "Selecione um plano",
      (p) => p.label,
    );
    fillSelect(
      $("#books-plan"),
      current.plans,
      "Selecione um plano",
      (p) => p.label,
    );
    const draft = drafts[scope] || {
      manual: blank(),
      finance: { request_key: crypto.randomUUID() },
    };
    await restoreManual(draft.manual);
    const f = $("#finance-form");
    f.reset();
    for (const [key, value] of Object.entries(draft.finance))
      if (f.elements[key]) f.elements[key].value = value;
    if (!companyId()) {
      renderManual([]);
      renderFinance([]);
      $("#books-exports").replaceChildren();
      return;
    }
    const query = { company_id: companyId(), period_id: periodId() },
      [manual, finance, exports] = await Promise.all([
        api("manual-journals", query),
        api("finance-titles", query),
        api("accounting-book-exports", { company_id: companyId() }),
      ]);
    if (v !== version) return;
    renderManual(manual);
    renderFinance(finance);
    const area = $("#books-exports");
    area.replaceChildren();
    exports
      .filter((row) => !periodId() || String(row.period_id) === periodId())
      .forEach((row) => {
        const card = element("article");
        card.className = "card";
        card.append(
          element("h3", "Exportação dos livros #" + row.id),
          element("p", "Plano #" + row.plan_id + " · " + row.book_hash),
        );
        row.artifacts.forEach((file) =>
          actionButton(card, "Baixar " + file.name, () =>
            download(
              "accounting-book-file",
              { company_id: companyId(), export_id: row.id, name: file.name },
              file.name,
              file,
            ),
          ),
        );
        area.append(card);
      });
  }
  function init() {
    try {
      drafts = JSON.parse(sessionStorage.getItem(storage) || "{}");
    } catch {
      drafts = {};
    }
    $("#manual-form").addEventListener("input", save);
    $("#finance-form").addEventListener("input", save);
    $("#manual-plan").addEventListener("change", async () => {
      const request = ++manualGeneration,
        company = companyId(),
        plan = $("#manual-plan").value;
      const accountControls = () => [
        ...document.querySelectorAll(".manual-line [data-key=account_id]"),
      ];
      setBusy(1);
      try {
        save();
        accountControls().forEach((control) => (control.disabled = true));
        const resolved = plan
          ? await api("accounts", { company_id: company, plan_id: plan })
          : [];
        if (
          request !== manualGeneration ||
          company !== companyId() ||
          plan !== $("#manual-plan").value
        )
          return;
        accounts = resolved;
        // Refresh only account choices. Keep fields typed while the request was pending.
        accountControls().forEach((control) => {
          fillSelect(
            control,
            accounts.filter((account) => account.kind === "analitica"),
            "Selecione a conta",
            (account) => account.code + " · " + account.description,
          );
          control.disabled = false;
        });
        save();
      } catch (e) {
        if (request === manualGeneration) {
          accounts = [];
          accountControls().forEach((control) => {
            fillSelect(
              control,
              [],
              "Contas indisponíveis; selecione o plano novamente",
              () => "",
            );
            control.disabled = false;
          });
          notice(e.message, true);
        }
      } finally {
        setBusy(-1);
      }
    });
    $("#manual-add").onclick = () => {
      save();
      lines([...drafts[scope].manual.lines, ...defaultLines().slice(0, 1)]);
      save();
    };
    $("#manual-new").onclick = async () => {
      await restoreManual(blank());
      save();
    };
    bindForm("#manual-form", async (f) => {
      save();
      const d = drafts[scope].manual;
      if (!periodId()) throw Error("Selecione a competência dos movimentos.");
      await api(
        "manual-journals",
        {
          ...d,
          company_id: companyId(),
          period_id: periodId(),
          journal_id: d.journal_id || null,
          expected_version: Number(d.expected_version),
          entries: d.lines.map((line) => ({
            ...line,
            amount: line.amount.replace(",", "."),
          })),
        },
        "POST",
      );
      await restoreManual(blank());
      save();
      await loadContext();
      return {
        message:
          "Prévia manual salva. Confira, revise e feche para incluir nos livros.",
      };
    });
    bindForm("#finance-form", async (f) => {
      if (!periodId()) throw Error("Selecione a competência do título.");
      const d = formObject(f);
      await api(
        "finance-titles",
        {
          ...d,
          amount: d.amount.replace(",", "."),
          company_id: companyId(),
          period_id: periodId(),
        },
        "POST",
      );
      f.reset();
      f.elements.request_key.value = crypto.randomUUID();
      save();
      await loadContext();
    });
    $("#finance-download").onclick = () =>
      download(
        "finance-file",
        { company_id: companyId(), period_id: periodId() },
        "financeiro.csv",
      ).catch((e) => notice(e.message, true));
    $("#books-plan").addEventListener("change", () => {
      books = null;
      $("#books-export-form").hidden = true;
      $("#books-summary").textContent =
        "Consulte os livros do plano selecionado.";
      table("#books-preview", []);
    });
    bindForm("#books-form", async (f) => {
      if (!periodId()) throw Error("Selecione a competência dos livros.");
      books = await api("accounting-books", {
        company_id: companyId(),
        period_id: periodId(),
        plan_id: f.elements.plan_id.value,
      });
      $("#books-summary").textContent =
        `Débitos ${books.totals.debit} · Créditos ${books.totals.credit} · ${books.sources.length} origem(ns) fechada(s) · ${books.book_hash}`;
      table("#books-preview", books.trial_balance_movements);
      $("#books-export-form").hidden = !books.sources.length;
      return { message: "Livros de movimentos consultados." };
    });
    bindForm("#books-export-form", async (f) => {
      if (!books) throw Error("Consulte os livros novamente.");
      await api(
        "accounting-book-exports",
        {
          company_id: books.company.id,
          period_id: books.period.id,
          plan_id: books.plan.id,
          book_hash: books.book_hash,
          reason: f.elements.reason.value,
        },
        "POST",
      );
      await loadContext();
    });
  }
  return { init, load, save, clearDrafts, clearView };
})();
