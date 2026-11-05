/* Template pré-compilado: não requer eval no navegador. */
var _Vue=Vue; var WorkRender=function render(_ctx, _cache) {
  with (_ctx) {
    const { createElementVNode: _createElementVNode, renderList: _renderList, Fragment: _Fragment, openBlock: _openBlock, createElementBlock: _createElementBlock, toDisplayString: _toDisplayString, vModelSelect: _vModelSelect, withDirectives: _withDirectives, createTextVNode: _createTextVNode, createCommentVNode: _createCommentVNode, normalizeClass: _normalizeClass, vModelText: _vModelText, withModifiers: _withModifiers, resolveComponent: _resolveComponent, createVNode: _createVNode, vShow: _vShow, vModelCheckbox: _vModelCheckbox } = _Vue

    const _component_data_table = _resolveComponent("data-table")

    return (_openBlock(), _createElementBlock("div", {
      class: "workbench",
      "aria-busy": busy
    }, [
      _createElementVNode("header", { class: "work-brand" }, [_createElementVNode("img", {
        src: "/assets/symbol.svg",
        alt: "",
        width: "32"
      }), _createElementVNode("strong", null, "Escritura"), _createElementVNode("span", null, "Escrituração fiscal e contábil")]),
      _createElementVNode("div", { class: "context" }, [
        _createElementVNode("label", null, [_createTextVNode("Empresa"), _withDirectives(_createElementVNode("select", {
          "aria-label": "Empresa",
          id: "company",
          disabled: busy,
          "onUpdate:modelValue": $event => ((company) = $event),
          onChange: switchCompany
        }, [_createElementVNode("option", { value: "" }, "Selecione"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(companies, (c) => {
          return (_openBlock(), _createElementBlock("option", { value: String(c.id) }, _toDisplayString(c.name), 9, ["value"]))
        }), 256))], 40, ["disabled", "onUpdate:modelValue", "onChange"]), [[_vModelSelect, company]])]),
        _createElementVNode("label", null, [_createTextVNode("Competência dos movimentos"), _withDirectives(_createElementVNode("select", {
          "aria-label": "Competência dos movimentos",
          id: "period",
          disabled: busy,
          "onUpdate:modelValue": $event => ((cycleId) = $event),
          onChange: switchCycle
        }, [_createElementVNode("option", { value: "" }, "Recepção sem competência"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(cycles, (c) => {
          return (_openBlock(), _createElementBlock("option", { value: String(c.id) }, _toDisplayString(c.competence) + " · " + _toDisplayString(c.state), 9, ["value"]))
        }), 256))], 40, ["disabled", "onUpdate:modelValue", "onChange"]), [[_vModelSelect, cycleId]])]),
        _createElementVNode("button", {
          onClick: refresh,
          disabled: busy
        }, "Atualizar", 8, ["onClick", "disabled"]),
        cycle
          ? (_openBlock(), _createElementBlock("span", { key: 0 }, "Parâmetros " + _toDisplayString(cycle.period.reference_competence) + " · " + _toDisplayString(cycle.plan?.label||'Plano a definir'), 1))
          : _createCommentVNode("", true)
      ]),
      _createElementVNode("nav", {
        class: "work-nav",
        "aria-label": "Recursos de escrituração"
      }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(resources, (r) => {
        return (_openBlock(), _createElementBlock("button", {
          onClick: $event => (navigate(r.id)),
          class: _normalizeClass({active:page===r.id})
        }, _toDisplayString(r.label), 11, ["onClick"]))
      }), 256))]),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 0,
            class: "alert error",
            role: "alert"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      notice
        ? (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "alert",
            role: "status"
          }, _toDisplayString(notice), 1))
        : _createCommentVNode("", true),
      _withDirectives(_createElementVNode("section", { class: "card" }, [
        _createElementVNode("h1", null, "Competências de trabalho"),
        _createElementVNode("p", null, "Informe a referência dos parâmetros separadamente do mês em que os movimentos serão registrados. O recebimento de arquivos já está disponível."),
        _createElementVNode("form", {
          onSubmit: _withModifiers(saveCycle, ["prevent"]),
          class: "grid"
        }, [
          _createElementVNode("label", null, [_createTextVNode("Movimentos"), _withDirectives(_createElementVNode("input", {
            type: "month",
            "onUpdate:modelValue": $event => ((config.competence) = $event),
            required: ""
          }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, config.competence]])]),
          _createElementVNode("label", null, [_createTextVNode("Referência dos parâmetros"), _withDirectives(_createElementVNode("input", {
            type: "month",
            "onUpdate:modelValue": $event => ((config.reference_competence) = $event),
            required: ""
          }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, config.reference_competence]])]),
          _createElementVNode("label", null, [_createTextVNode("Plano"), _withDirectives(_createElementVNode("select", {
            "aria-label": "Plano",
            "onUpdate:modelValue": $event => ((config.plan_id) = $event)
          }, [_createElementVNode("option", { value: "" }, "Definir depois"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(plans, (p) => {
            return (_openBlock(), _createElementBlock("option", { value: p.id }, _toDisplayString(p.label) + " · v" + _toDisplayString(p.version), 9, ["value"]))
          }), 256))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, config.plan_id]])]),
          _createElementVNode("label", null, [_createTextVNode("Motivo"), _withDirectives(_createElementVNode("input", {
            "onUpdate:modelValue": $event => ((config.reason) = $event),
            required: ""
          }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, config.reason]])]),
          _createElementVNode("button", { disabled: busy }, "Salvar competência", 8, ["disabled"]),
          _createElementVNode("button", {
            type: "button",
            onClick: editCycle
          }, "Editar competência selecionada", 8, ["onClick"])
        ], 40, ["onSubmit"]),
        _createVNode(_component_data_table, {
          rows: cycles,
          columns: {competence:'Movimentos','period.reference_competence':'Parâmetros','plan.label':'Plano',state:'Situação',version:'Versão'}
        }, null, 8, ["rows", "columns"])
      ], 512), [[_vShow, page==='setup']]),
      _withDirectives(_createElementVNode("section", { class: "card" }, [
        _createElementVNode("h1", null, "Plano de contas e políticas de escrituração"),
        _createElementVNode("p", null, "Importe uma versão completa do plano em CSV. Colunas: codigo;descricao;tipo;natureza;superior. Tipo sintetica/analitica e natureza devedora/credora. Outras colunas são preservadas como atributos. O original fica vinculado à versão."),
        _createElementVNode("form", {
          onSubmit: _withModifiers(importPlan, ["prevent"]),
          class: "grid"
        }, [
          _createElementVNode("label", null, [_createTextVNode("Nome da versão"), _withDirectives(_createElementVNode("input", {
            "onUpdate:modelValue": $event => ((planForm.label) = $event),
            required: ""
          }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, planForm.label]])]),
          _createElementVNode("label", null, [_createTextVNode("Arquivo CSV"), _createElementVNode("input", {
            type: "file",
            accept: ".csv",
            onChange: $event => (planFile=$event.target.files[0]),
            required: ""
          }, null, 40, ["onChange"])]),
          _createElementVNode("label", null, [_createTextVNode("Motivo"), _withDirectives(_createElementVNode("input", {
            "onUpdate:modelValue": $event => ((planForm.reason) = $event),
            required: ""
          }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, planForm.reason]])]),
          _createElementVNode("button", { disabled: busy }, "Importar plano", 8, ["disabled"])
        ], 40, ["onSubmit"]),
        _createElementVNode("label", null, [_createTextVNode("Consultar plano"), _withDirectives(_createElementVNode("select", {
          "aria-label": "Consultar plano",
          "onUpdate:modelValue": $event => ((viewPlan) = $event),
          onChange: loadAccounts
        }, [_createElementVNode("option", { value: "" }, "Selecione"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(plans, (p) => {
          return (_openBlock(), _createElementBlock("option", { value: p.id }, _toDisplayString(p.label) + " · v" + _toDisplayString(p.version), 9, ["value"]))
        }), 256))], 40, ["onUpdate:modelValue", "onChange"]), [[_vModelSelect, viewPlan]])]),
        _createVNode(_component_data_table, {
          rows: accounts,
          columns: {code:'Código',description:'Descrição',kind:'Tipo',nature:'Natureza',parent_code:'Superior',attributes:'Atributos'}
        }, null, 8, ["rows", "columns"]),
        _createElementVNode("h2", null, "Política explícita por operação e referência"),
        _createElementVNode("form", {
          onSubmit: _withModifiers(savePolicy, ["prevent"]),
          class: "grid"
        }, [
          _createElementVNode("label", null, [_createTextVNode("Plano"), _withDirectives(_createElementVNode("select", {
            "aria-label": "Plano",
            "onUpdate:modelValue": $event => ((policyForm.plan_id) = $event),
            onChange: loadPolicyAccounts,
            required: ""
          }, [_createElementVNode("option", { value: "" }, "Selecione"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(plans, (p) => {
            return (_openBlock(), _createElementBlock("option", { value: p.id }, _toDisplayString(p.label), 9, ["value"]))
          }), 256))], 40, ["onUpdate:modelValue", "onChange"]), [[_vModelSelect, policyForm.plan_id]])]),
          _createElementVNode("label", null, [_createTextVNode("Operação"), _withDirectives(_createElementVNode("select", {
            "aria-label": "Operação",
            "onUpdate:modelValue": $event => ((policyForm.operation) = $event)
          }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(operations, (o) => {
            return (_openBlock(), _createElementBlock("option", { value: o.id }, _toDisplayString(o.label), 9, ["value"]))
          }), 256))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, policyForm.operation]])]),
          _createElementVNode("label", null, [_createTextVNode("Referência"), _withDirectives(_createElementVNode("input", {
            type: "month",
            "onUpdate:modelValue": $event => ((policyForm.reference_competence) = $event),
            required: ""
          }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, policyForm.reference_competence]])]),
          _createElementVNode("label", null, [_createTextVNode("Nome"), _withDirectives(_createElementVNode("input", {
            "onUpdate:modelValue": $event => ((policyForm.label) = $event),
            required: ""
          }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, policyForm.label]])]),
          _createElementVNode("label", null, [_createTextVNode("Débito"), _withDirectives(_createElementVNode("select", {
            "aria-label": "Débito",
            "onUpdate:modelValue": $event => ((policyForm.debit_account_id) = $event),
            required: ""
          }, [_createElementVNode("option", { value: "" }, "Selecione"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(policyAccounts.filter(a=>a.kind==='analitica'), (a) => {
            return (_openBlock(), _createElementBlock("option", { value: a.id }, _toDisplayString(a.code) + " · " + _toDisplayString(a.description), 9, ["value"]))
          }), 256))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, policyForm.debit_account_id]])]),
          _createElementVNode("label", null, [_createTextVNode("Crédito"), _withDirectives(_createElementVNode("select", {
            "aria-label": "Crédito",
            "onUpdate:modelValue": $event => ((policyForm.credit_account_id) = $event),
            required: ""
          }, [_createElementVNode("option", { value: "" }, "Selecione"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(policyAccounts.filter(a=>a.kind==='analitica'), (a) => {
            return (_openBlock(), _createElementBlock("option", { value: a.id }, _toDisplayString(a.code) + " · " + _toDisplayString(a.description), 9, ["value"]))
          }), 256))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, policyForm.credit_account_id]])]),
          _createElementVNode("label", null, [_createTextVNode("Motivo"), _withDirectives(_createElementVNode("input", {
            "onUpdate:modelValue": $event => ((policyForm.reason) = $event),
            required: ""
          }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, policyForm.reason]])]),
          _createElementVNode("label", null, [_withDirectives(_createElementVNode("input", {
            type: "checkbox",
            "onUpdate:modelValue": $event => ((policyForm.approved) = $event)
          }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, policyForm.approved]]), _createTextVNode(" Aprovo as contas para esta operação")]),
          _createElementVNode("button", { disabled: busy }, "Registrar versão da política", 8, ["disabled"])
        ], 40, ["onSubmit"]),
        _createVNode(_component_data_table, {
          rows: policies,
          columns: {label:'Política',operation:'Operação',reference_competence:'Referência',version:'Versão',state:'Estado',debit_account_id:'Débito',credit_account_id:'Crédito'}
        }, null, 8, ["rows", "columns"])
      ], 512), [[_vShow, page==='chart']]),
      _withDirectives(_createElementVNode("section", { class: "card" }, [
        _createElementVNode("h1", null, "Recepção e caixa de entrada"),
        _createElementVNode("p", null, "Receba primeiro; escolha a competência ao organizar. Nenhum lançamento é criado pelo envio. XML, SPED e ZIP; 7z/RAR dependem do leitor disponível e não estão disponíveis no Windows congelado atual."),
        _createElementVNode("form", {
          onSubmit: _withModifiers(receive, ["prevent"]),
          class: "grid"
        }, [_createElementVNode("label", null, [_createTextVNode("Arquivos"), _createElementVNode("input", {
          id: "source-files",
          type: "file",
          multiple: "",
          accept: ".xml,.txt,.sped,.zip,.7z,.rar",
          onChange: $event => {inputFiles=Array.from($event.target.files);receiveKey=key()},
          required: ""
        }, null, 40, ["onChange"])]), _createElementVNode("button", { disabled: busy||!company }, "Receber arquivos", 8, ["disabled"])], 40, ["onSubmit"]),
        _createElementVNode("p", null, "Até 10 MiB por envio web, 500 entradas após expansão e 100 MiB expandidos. Originais, decisões e erros ficam preservados."),
        _createElementVNode("label", null, [_createTextVNode("Motivo da organização / retirada"), _withDirectives(_createElementVNode("input", {
          "onUpdate:modelValue": $event => ((sourceReason) = $event),
          placeholder: "Informe sua decisão"
        }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, sourceReason]])]),
        _createElementVNode("label", null, [_createTextVNode("Perfil para SPED"), _withDirectives(_createElementVNode("select", {
          "aria-label": "Perfil para SPED",
          "onUpdate:modelValue": $event => ((spedProfile) = $event)
        }, [_createElementVNode("option", { value: "" }, "Preservar original"), _createElementVNode("option", { value: "efd-icms-ipi-020-c100-v2" }, "EFD ICMS/IPI 020 · C100 parcial")], 8, ["onUpdate:modelValue"]), [[_vModelSelect, spedProfile]])]),
        _createElementVNode("div", { class: "table-scroll" }, [_createElementVNode("table", null, [_createElementVNode("thead", null, [_createElementVNode("tr", null, [
          _createElementVNode("th", null, "Origem"),
          _createElementVNode("th", null, "Identificação"),
          _createElementVNode("th", null, "Situação / pendências"),
          _createElementVNode("th", null, "Decisão")
        ])]), _createElementVNode("tbody", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(inbox, (s) => {
          return (_openBlock(), _createElementBlock("tr", { key: s.input_id }, [
            _createElementVNode("td", null, [_createTextVNode(_toDisplayString(s.filename), 1), _createElementVNode("small", null, "#" + _toDisplayString(s.input_id) + " · " + _toDisplayString(s.kind) + " · " + _toDisplayString(s.size) + " bytes", 1), _createElementVNode("a", {
              href: download('source-original',{input_id:s.input_id}),
              onClick: _withModifiers($event => (downloadFile('source-original',{input_id:s.input_id},s.filename)), ["prevent"])
            }, "Original", 8, ["href", "onClick"])]),
            _createElementVNode("td", null, [(s.evidence.number)
              ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [_createTextVNode(_toDisplayString(s.evidence.model) + " / " + _toDisplayString(s.evidence.number) + " · " + _toDisplayString(s.evidence.total), 1), _createElementVNode("small", null, "Emissão " + _toDisplayString(s.evidence.issued_date) + " · competência sugerida " + _toDisplayString(s.evidence.suggested_competence), 1), _createElementVNode("small", null, "Emitente " + _toDisplayString(s.evidence.issuer) + " · destinatário " + _toDisplayString(s.evidence.buyer||'não informado'), 1)], 64))
              : (_openBlock(), _createElementBlock("span", { key: 1 }, _toDisplayString(s.evidence.records?(s.evidence.records+' registros estruturais'):'Original preservado'), 1))]),
            _createElementVNode("td", null, [_createTextVNode(_toDisplayString(s.evidence.state), 1), _createElementVNode("small", null, _toDisplayString((s.evidence.issues||[]).join('; ')), 1)]),
            _createElementVNode("td", null, [
              _createElementVNode("button", { onClick: $event => (showSourceHistory(s)) }, "Decisões e versões", 8, ["onClick"]),
              ((!s.file_id || s.evidence.state==='pendente') && !['pacote','descartado'].includes(s.evidence.state))
                ? (_openBlock(), _createElementBlock("button", {
                    key: 0,
                    onClick: $event => (organize(s)),
                    disabled: busy||!cycle
                  }, "Organizar em " + _toDisplayString(cycle?.competence||'competência'), 9, ["onClick", "disabled"]))
                : _createCommentVNode("", true),
              (!s.file_id && s.evidence.state!=='descartado')
                ? (_openBlock(), _createElementBlock("button", {
                    key: 1,
                    onClick: $event => (discard(s)),
                    disabled: busy
                  }, "Retirar da fila", 8, ["onClick", "disabled"]))
                : _createCommentVNode("", true),
              (s.file_id)
                ? (_openBlock(), _createElementBlock("button", {
                    key: 2,
                    onClick: $event => (showImpact(s))
                  }, "Dependências / retirada", 8, ["onClick"]))
                : _createCommentVNode("", true)
            ])
          ]))
        }), 128))])])]),
        sourceHistory
          ? (_openBlock(), _createElementBlock("article", {
              key: 0,
              class: "inset"
            }, [_createElementVNode("h2", null, "Decisões · " + _toDisplayString(sourceHistory.filename), 1), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(sourceHistory.revisions, (r) => {
              return (_openBlock(), _createElementBlock("details", null, [_createElementVNode("summary", null, "Versão " + _toDisplayString(r.version) + " · " + _toDisplayString(r.evidence.state) + " · " + _toDisplayString(r.reason), 1), _createElementVNode("small", null, _toDisplayString(r.created_at) + " · responsável " + _toDisplayString(r.actor), 1), _createElementVNode("pre", null, _toDisplayString(JSON.stringify(r.evidence,null,2)), 1)]))
            }), 256))]))
          : _createCommentVNode("", true),
        impact
          ? (_openBlock(), _createElementBlock("article", {
              key: 1,
              class: "inset"
            }, [
              _createElementVNode("h2", null, "Consequências da retirada"),
              _createElementVNode("pre", null, _toDisplayString(JSON.stringify(impact,null,2)), 1),
              _createElementVNode("label", null, [_withDirectives(_createElementVNode("input", {
                type: "checkbox",
                "onUpdate:modelValue": $event => ((impactConfirmed) = $event)
              }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, impactConfirmed]]), _createTextVNode(" Conferi as dependências e confirmo a retirada lógica")]),
              _createElementVNode("button", {
                onClick: removeSource,
                disabled: busy||!impactConfirmed||impact.protected.length
              }, "Confirmar retirada preservando original", 8, ["onClick", "disabled"])
            ]))
          : _createCommentVNode("", true)
      ], 512), [[_vShow, page==='imports']]),
      _withDirectives(_createElementVNode("section", { class: "card" }, [
        _createElementVNode("h1", null, "Escrituração"),
        _createElementVNode("p", null, "Importe documentos ou registre manualmente. Confira fatos fiscais, partidas e cobrança na mesma operação; a efetivação gera movimentos e títulos juntos."),
        overview
          ? (_openBlock(), _createElementBlock("div", {
              key: 0,
              class: "metrics"
            }, [
              _createElementVNode("span", null, [_createTextVNode("A escriturar "), _createElementVNode("b", null, _toDisplayString(overview.counts.pending_documents), 1)]),
              _createElementVNode("span", null, [_createTextVNode("Rascunhos "), _createElementVNode("b", null, _toDisplayString(overview.counts.drafts), 1)]),
              _createElementVNode("span", null, [_createTextVNode("Conferidos "), _createElementVNode("b", null, _toDisplayString(overview.counts.reviewed), 1)]),
              _createElementVNode("span", null, [_createTextVNode("Escriturados "), _createElementVNode("b", null, _toDisplayString(overview.counts.posted), 1)])
            ]))
          : _createCommentVNode("", true),
        _createElementVNode("div", { class: "toolbar" }, [_createElementVNode("button", {
          id: "new-operation",
          onClick: $event => (newOperation()),
          disabled: busy||!cycle
        }, "+ Lançamento manual", 8, ["onClick", "disabled"]), _createElementVNode("button", {
          onClick: newOpening,
          disabled: busy||!cycle
        }, "Saldos iniciais", 8, ["onClick", "disabled"])]),
        _createElementVNode("div", { class: "table-scroll" }, [_createElementVNode("table", null, [_createElementVNode("thead", null, [_createElementVNode("tr", null, [
          _createElementVNode("th", null, "Documento organizado"),
          _createElementVNode("th", null, "Valor"),
          _createElementVNode("th", null, "Situação"),
          _createElementVNode("th")
        ])]), _createElementVNode("tbody", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(overview?.documents||[], (d) => {
          return (_openBlock(), _createElementBlock("tr", null, [
            _createElementVNode("td", null, "#" + _toDisplayString(d.id) + " · " + _toDisplayString(d.model) + " / " + _toDisplayString(d.number), 1),
            _createElementVNode("td", null, _toDisplayString(d.total), 1),
            _createElementVNode("td", null, _toDisplayString(d.state), 1),
            _createElementVNode("td", null, [(d.operation_id)
              ? (_openBlock(), _createElementBlock("button", {
                  key: 0,
                  onClick: $event => (openOperation(d.operation_id))
                }, "Abrir operação", 8, ["onClick"]))
              : (d.state!=='legado')
                ? (_openBlock(), _createElementBlock("button", {
                    key: 1,
                    onClick: $event => (prepareDocument(d))
                  }, "Escriturar documento", 8, ["onClick"]))
                : (_openBlock(), _createElementBlock("span", { key: 2 }, "Preservado no histórico"))])
          ]))
        }), 256))])])]),
        sourceChoice
          ? (_openBlock(), _createElementBlock("div", {
              key: 1,
              class: "inset"
            }, [_createElementVNode("h2", null, "Escolha a evidência documental"), _createElementVNode("label", null, [_createTextVNode("Fonte"), _withDirectives(_createElementVNode("select", {
              "aria-label": "Fonte",
              "onUpdate:modelValue": $event => ((chosenObservation) = $event)
            }, [_createElementVNode("option", { value: "" }, "Selecione"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(sourceChoice.source.observations, (o) => {
              return (_openBlock(), _createElementBlock("option", { value: o.id }, _toDisplayString(o.filename||('Arquivo #'+o.file_id)) + " · " + _toDisplayString(o.locator) + " · " + _toDisplayString(o.normalized.total), 9, ["value"]))
            }), 256))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, chosenObservation]])]), _createElementVNode("button", { onClick: prepareChosen }, "Preparar fonte escolhida", 8, ["onClick"])]))
          : _createCommentVNode("", true)
      ], 512), [[_vShow, page==='accounting']]),
      _withDirectives(_createElementVNode("nav", {
        class: "draft-tabs",
        "aria-label": "Fichas de escrituração"
      }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(tabs, (t) => {
        return (_openBlock(), _createElementBlock("button", {
          class: _normalizeClass({active:activeTab===t.id}),
          onClick: $event => (selectTab(t.id))
        }, [_createTextVNode(_toDisplayString(t.title) + " ", 1), _createElementVNode("span", { onClick: _withModifiers($event => (closeTab(t)), ["stop"]) }, "×", 8, ["onClick"])], 10, ["onClick"]))
      }), 256))], 512), [[_vShow, ['accounting','reconciliation'].includes(page)]]),
      (active && ['accounting','reconciliation'].includes(page))
        ? (_openBlock(), _createElementBlock("section", {
            key: 2,
            class: "card operation"
          }, [
            _createElementVNode("header", null, [_createElementVNode("h2", null, _toDisplayString(active.title), 1), _createElementVNode("span", null, _toDisplayString(active.operation?.state||'Rascunho da guia') + " · " + _toDisplayString(active.operation?'v'+active.operation.version:'não efetivado'), 1), _createElementVNode("small", null, _toDisplayString(draftStatus), 1)]),
            _createElementVNode("form", { onSubmit: _withModifiers(saveOperation, ["prevent"]) }, [_createElementVNode("fieldset", { disabled: busy||['escriturado','dispensado'].includes(active.operation?.state) }, [
              _createElementVNode("div", { class: "grid" }, [
                _createElementVNode("label", null, [_createTextVNode("Referência"), _withDirectives(_createElementVNode("input", {
                  id: "operation-reference",
                  "onUpdate:modelValue": $event => ((active.data.payload.reference) = $event)
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, active.data.payload.reference]])]),
                _createElementVNode("label", null, [_createTextVNode("Natureza"), _withDirectives(_createElementVNode("select", {
                  "aria-label": "Natureza",
                  "onUpdate:modelValue": $event => ((active.data.payload.fiscal.operation) = $event)
                }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(operations, (o) => {
                  return (_openBlock(), _createElementBlock("option", { value: o.id }, _toDisplayString(o.label), 9, ["value"]))
                }), 256))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, active.data.payload.fiscal.operation]])]),
                _createElementVNode("label", null, [_createTextVNode("Data de escrituração"), _withDirectives(_createElementVNode("input", {
                  type: "date",
                  "onUpdate:modelValue": $event => ((active.data.payload.fiscal.posting_date) = $event),
                  onChange: syncDates
                }, null, 40, ["onUpdate:modelValue", "onChange"]), [[_vModelText, active.data.payload.fiscal.posting_date]])]),
                _createElementVNode("label", null, [_createTextVNode("Valor total"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((active.data.payload.fiscal.total) = $event),
                  inputmode: "decimal",
                  onChange: syncAmounts
                }, null, 40, ["onUpdate:modelValue", "onChange"]), [[_vModelText, active.data.payload.fiscal.total]])]),
                _createElementVNode("label", null, [_createTextVNode("Política"), _withDirectives(_createElementVNode("select", {
                  "aria-label": "Política",
                  "onUpdate:modelValue": $event => ((active.data.payload.policy_id) = $event)
                }, [_createElementVNode("option", { value: null }, "Partidas informadas manualmente", 8, ["value"]), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(applicablePolicies, (p) => {
                  return (_openBlock(), _createElementBlock("option", { value: p.id }, _toDisplayString(p.label) + " · v" + _toDisplayString(p.version), 9, ["value"]))
                }), 256))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, active.data.payload.policy_id]])]),
                _createElementVNode("button", {
                  type: "button",
                  onClick: applyPolicy
                }, "Aplicar contas da política", 8, ["onClick"])
              ]),
              _createElementVNode("details", { open: ['entrada','saida','servico_tomado','servico_prestado'].includes(active.data.payload.fiscal.operation) }, [_createElementVNode("summary", null, "Documento e fatos fiscais informados"), _createElementVNode("div", { class: "grid" }, [
                _createElementVNode("label", null, [_createTextVNode("Modelo"), _withDirectives(_createElementVNode("select", {
                  "aria-label": "Modelo",
                  "onUpdate:modelValue": $event => ((active.data.payload.fiscal.model) = $event)
                }, [
                  _createElementVNode("option", { value: "" }, "Sem documento fiscal"),
                  _createElementVNode("option", { value: "55" }, "55 · NF-e"),
                  _createElementVNode("option", { value: "65" }, "65 · NFC-e"),
                  _createElementVNode("option", { value: "SERVICO" }, "Serviço")
                ], 8, ["onUpdate:modelValue"]), [[_vModelSelect, active.data.payload.fiscal.model]])]),
                _createElementVNode("label", null, [_createTextVNode("Número"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((active.data.payload.fiscal.number) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, active.data.payload.fiscal.number]])]),
                _createElementVNode("label", null, [_createTextVNode("Série"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((active.data.payload.fiscal.series) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, active.data.payload.fiscal.series]])]),
                _createElementVNode("label", null, [_createTextVNode("Emissão"), _withDirectives(_createElementVNode("input", {
                  type: "date",
                  "onUpdate:modelValue": $event => ((active.data.payload.fiscal.issued_date) = $event)
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, active.data.payload.fiscal.issued_date]])]),
                _createElementVNode("label", null, [_createTextVNode("Emitente · CPF/CNPJ"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((active.data.payload.fiscal.issuer) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, active.data.payload.fiscal.issuer]])]),
                _createElementVNode("label", null, [_createTextVNode("Destinatário · CPF/CNPJ"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((active.data.payload.fiscal.buyer) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, active.data.payload.fiscal.buyer]])]),
                _createElementVNode("label", null, [_createTextVNode("CFOP informado"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((active.data.payload.fiscal.cfop) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, active.data.payload.fiscal.cfop]])]),
                _createElementVNode("label", null, [_createTextVNode("CST informado"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((active.data.payload.fiscal.cst) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, active.data.payload.fiscal.cst]])]),
                _createElementVNode("label", null, [_createTextVNode("Base ICMS informada"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((active.data.payload.fiscal.icms_base) = $event),
                  inputmode: "decimal"
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, active.data.payload.fiscal.icms_base]])]),
                _createElementVNode("label", null, [_createTextVNode("ICMS informado"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((active.data.payload.fiscal.icms_amount) = $event),
                  inputmode: "decimal"
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, active.data.payload.fiscal.icms_amount]])]),
                _createElementVNode("label", null, [_createTextVNode("Base ISS informada"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((active.data.payload.fiscal.iss_base) = $event),
                  inputmode: "decimal"
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, active.data.payload.fiscal.iss_base]])]),
                _createElementVNode("label", null, [_createTextVNode("ISS informado"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((active.data.payload.fiscal.iss_amount) = $event),
                  inputmode: "decimal"
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, active.data.payload.fiscal.iss_amount]])])
              ]), _createElementVNode("p", null, "Valores informados pelo operador ou pela origem; não há cálculo tributário nem homologação de obrigação fiscal.")], 8, ["open"]),
              _createElementVNode("label", null, [_withDirectives(_createElementVNode("input", {
                type: "checkbox",
                "onUpdate:modelValue": $event => ((active.data.payload.acknowledge_differences) = $event)
              }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, active.data.payload.acknowledge_differences]]), _createTextVNode(" Conferi divergências entre as fontes")]),
              (active.data.payload.fiscal.operation==='abertura')
                ? (_openBlock(), _createElementBlock("label", { key: 0 }, [_withDirectives(_createElementVNode("input", {
                    type: "checkbox",
                    "onUpdate:modelValue": $event => ((active.data.payload.opening_zero) = $event),
                    onChange: toggleZero
                  }, null, 40, ["onUpdate:modelValue", "onChange"]), [[_vModelCheckbox, active.data.payload.opening_zero]]), _createTextVNode(" Confirmo que os saldos iniciais são zero")]))
                : _createCommentVNode("", true),
              _createElementVNode("h3", null, "Partidas contábeis"),
              _createElementVNode("div", { class: "table-scroll" }, [_createElementVNode("table", null, [_createElementVNode("thead", null, [_createElementVNode("tr", null, [
                _createElementVNode("th", null, "Conta analítica"),
                _createElementVNode("th", null, "D/C"),
                _createElementVNode("th", null, "Data"),
                _createElementVNode("th", null, "Valor"),
                _createElementVNode("th", null, "Grupo"),
                _createElementVNode("th", null, "Histórico"),
                _createElementVNode("th")
              ])]), _createElementVNode("tbody", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(active.data.payload.entries, (l, i) => {
                return (_openBlock(), _createElementBlock("tr", null, [
                  _createElementVNode("td", null, [_withDirectives(_createElementVNode("select", {
                    "aria-label": 'Conta '+(i+1),
                    "onUpdate:modelValue": $event => ((l.account_id) = $event)
                  }, [_createElementVNode("option", { value: "" }, "Selecione"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(cycleAccounts.filter(a=>a.kind==='analitica'), (a) => {
                    return (_openBlock(), _createElementBlock("option", { value: a.id }, _toDisplayString(a.code) + " · " + _toDisplayString(a.description), 9, ["value"]))
                  }), 256))], 8, ["aria-label", "onUpdate:modelValue"]), [[_vModelSelect, l.account_id]])]),
                  _createElementVNode("td", null, [_withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((l.side) = $event) }, [_createElementVNode("option", null, "D"), _createElementVNode("option", null, "C")], 8, ["onUpdate:modelValue"]), [[_vModelSelect, l.side]])]),
                  _createElementVNode("td", null, [_withDirectives(_createElementVNode("input", {
                    type: "date",
                    "onUpdate:modelValue": $event => ((l.date) = $event)
                  }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, l.date]])]),
                  _createElementVNode("td", null, [_withDirectives(_createElementVNode("input", {
                    "aria-label": 'Valor partida '+(i+1),
                    "onUpdate:modelValue": $event => ((l.amount) = $event),
                    inputmode: "decimal"
                  }, null, 8, ["aria-label", "onUpdate:modelValue"]), [[_vModelText, l.amount]])]),
                  _createElementVNode("td", null, [_withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((l.group) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, l.group]])]),
                  _createElementVNode("td", null, [_withDirectives(_createElementVNode("input", {
                    "aria-label": 'Histórico '+(i+1),
                    "onUpdate:modelValue": $event => ((l.memo) = $event)
                  }, null, 8, ["aria-label", "onUpdate:modelValue"]), [[_vModelText, l.memo]])]),
                  _createElementVNode("td", null, [_createElementVNode("button", {
                    type: "button",
                    onClick: $event => (active.data.payload.entries.splice(i,1))
                  }, "×", 8, ["onClick"])])
                ]))
              }), 256))])])]),
              _createElementVNode("button", {
                type: "button",
                onClick: addLine
              }, "+ Partida", 8, ["onClick"]),
              _createElementVNode("h3", null, "Cobrança"),
              _createElementVNode("div", { class: "grid" }, [
                _createElementVNode("label", null, [_createTextVNode("Tratamento"), _withDirectives(_createElementVNode("select", {
                  "aria-label": "Tratamento",
                  "onUpdate:modelValue": $event => ((active.data.payload.finance.mode) = $event)
                }, [_createElementVNode("option", { value: "sem_cobranca" }, "Sem nova cobrança"), _createElementVNode("option", {
                  value: "origem",
                  disabled: !active.data.payload.document_id
                }, "Parcelas da origem", 8, ["disabled"]), _createElementVNode("option", { value: "manual" }, "Cobrança informada")], 8, ["onUpdate:modelValue"]), [[_vModelSelect, active.data.payload.finance.mode]])]),
                (active.data.payload.finance.mode!=='sem_cobranca')
                  ? (_openBlock(), _createElementBlock("label", { key: 0 }, [_createTextVNode("Direção"), _withDirectives(_createElementVNode("select", {
                      "aria-label": "Direção",
                      "onUpdate:modelValue": $event => ((active.data.payload.finance.direction) = $event)
                    }, [_createElementVNode("option", { value: "pagar" }, "A pagar"), _createElementVNode("option", { value: "receber" }, "A receber")], 8, ["onUpdate:modelValue"]), [[_vModelSelect, active.data.payload.finance.direction]])]))
                  : _createCommentVNode("", true),
                (active.data.payload.finance.mode!=='sem_cobranca')
                  ? (_openBlock(), _createElementBlock("label", { key: 1 }, [_createTextVNode("Contraparte"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((active.data.payload.finance.counterparty) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, active.data.payload.finance.counterparty]])]))
                  : _createCommentVNode("", true),
                (active.data.payload.finance.mode==='manual')
                  ? (_openBlock(), _createElementBlock("label", { key: 2 }, [_createTextVNode("Motivo da cobrança manual"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((active.data.payload.finance.reason) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, active.data.payload.finance.reason]])]))
                  : _createCommentVNode("", true)
              ]),
              (active.data.payload.finance.mode!=='sem_cobranca')
                ? (_openBlock(), _createElementBlock("div", { key: 1 }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(active.data.payload.finance.installments, (p, i) => {
                    return (_openBlock(), _createElementBlock("div", { class: "grid" }, [
                      _createElementVNode("label", null, [_createTextVNode("Parcela"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((p.reference) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, p.reference]])]),
                      _createElementVNode("label", null, [_createTextVNode("Vencimento"), _withDirectives(_createElementVNode("input", {
                        type: "date",
                        "onUpdate:modelValue": $event => ((p.due_date) = $event)
                      }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, p.due_date]])]),
                      _createElementVNode("label", null, [_createTextVNode("Valor"), _withDirectives(_createElementVNode("input", {
                        "onUpdate:modelValue": $event => ((p.amount) = $event),
                        inputmode: "decimal"
                      }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, p.amount]])]),
                      _createElementVNode("label", null, [_createTextVNode("Título existente (ID, opcional)"), _withDirectives(_createElementVNode("input", {
                        "onUpdate:modelValue": $event => ((p.existing_title_id) = $event),
                        inputmode: "numeric"
                      }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, p.existing_title_id]])]),
                      _createElementVNode("button", {
                        type: "button",
                        onClick: $event => (active.data.payload.finance.installments.splice(i,1))
                      }, "Remover parcela", 8, ["onClick"])
                    ]))
                  }), 256)), _createElementVNode("button", {
                    type: "button",
                    onClick: $event => (active.data.payload.finance.installments.push({reference:'',due_date:'',amount:''}))
                  }, "+ Parcela", 8, ["onClick"])]))
                : _createCommentVNode("", true),
              _createElementVNode("label", null, [_createTextVNode("Observações"), _withDirectives(_createElementVNode("textarea", { "onUpdate:modelValue": $event => ((active.data.payload.notes) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, active.data.payload.notes]])])
            ], 8, ["disabled"]), _createElementVNode("label", null, [_createTextVNode("Motivo desta ação"), _withDirectives(_createElementVNode("input", {
              id: "operation-reason",
              disabled: busy,
              "onUpdate:modelValue": $event => ((active.data.reason) = $event),
              required: ""
            }, null, 8, ["disabled", "onUpdate:modelValue"]), [[_vModelText, active.data.reason]])]), _createElementVNode("div", { class: "toolbar" }, [
              _createElementVNode("button", { disabled: busy||['escriturado','dispensado'].includes(active.operation?.state) }, "Salvar versão", 8, ["disabled"]),
              _createElementVNode("button", {
                type: "button",
                onClick: flush,
                disabled: busy
              }, "Preservar rascunho da guia", 8, ["onClick", "disabled"]),
              _createElementVNode("button", {
                type: "button",
                onClick: $event => (review('revisado')),
                disabled: busy||active.operation?.state!=='rascunho'||dirty
              }, "Conferir versão", 8, ["onClick", "disabled"]),
              _createElementVNode("button", {
                type: "button",
                onClick: post,
                disabled: busy||active.operation?.state!=='revisado'||dirty
              }, "Escriturar", 8, ["onClick", "disabled"]),
              _createElementVNode("button", {
                type: "button",
                onClick: $event => (review('dispensado')),
                disabled: busy||active.operation?.state!=='rascunho'||dirty
              }, "Dispensar com motivo", 8, ["onClick", "disabled"])
            ])], 40, ["onSubmit"]),
            (active.operation)
              ? (_openBlock(), _createElementBlock("ul", {
                  key: 0,
                  class: "issues"
                }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(active.operation.validation.issues, (i) => {
                  return (_openBlock(), _createElementBlock("li", null, _toDisplayString(i.message), 1))
                }), 256))]))
              : _createCommentVNode("", true),
            (active.operation)
              ? (_openBlock(), _createElementBlock("details", { key: 1 }, [_createElementVNode("summary", null, "Evidência e histórico de versões"), _createElementVNode("pre", null, _toDisplayString(JSON.stringify({source:active.operation.payload.source_hash,history:active.operation.history,settlement:active.operation.payload.settlement,titles:active.operation.titles},null,2)), 1)]))
              : _createCommentVNode("", true),
            (active.operation?.state==='escriturado')
              ? (_openBlock(), _createElementBlock("form", {
                  key: 2,
                  onSubmit: _withModifiers(reverse, ["prevent"]),
                  class: "grid"
                }, [_createElementVNode("label", null, [_createTextVNode("Competência de destino do estorno"), _withDirectives(_createElementVNode("select", {
                  "aria-label": "Competência de destino do estorno",
                  "onUpdate:modelValue": $event => ((reversalCycleId) = $event)
                }, [_createElementVNode("option", { value: "" }, "Competência atual"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(cycles.filter(c=>c.state==='aberta'), (c) => {
                  return (_openBlock(), _createElementBlock("option", { value: String(c.id) }, _toDisplayString(c.competence), 9, ["value"]))
                }), 256))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, reversalCycleId]])]), _createElementVNode("label", null, [_createTextVNode("Data do estorno"), _withDirectives(_createElementVNode("input", {
                  type: "date",
                  "onUpdate:modelValue": $event => ((reversalDate) = $event),
                  required: ""
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, reversalDate]])]), _createElementVNode("button", { disabled: busy }, "Preparar estorno vinculado", 8, ["disabled"])], 40, ["onSubmit"]))
              : _createCommentVNode("", true)
          ]))
        : _createCommentVNode("", true),
      _withDirectives(_createElementVNode("section", { class: "card" }, [_createElementVNode("h1", null, "Conferência de operações"), _createElementVNode("p", null, "A conferência fixa a versão completa. Alterações posteriores exigem nova versão e conferência."), _createElementVNode("div", { class: "table-scroll" }, [_createElementVNode("table", null, [_createElementVNode("thead", null, [_createElementVNode("tr", null, [
        _createElementVNode("th", null, "Referência"),
        _createElementVNode("th", null, "Situação"),
        _createElementVNode("th", null, "Pendências"),
        _createElementVNode("th")
      ])]), _createElementVNode("tbody", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(overview?.operations||[], (o) => {
        return (_openBlock(), _createElementBlock("tr", null, [
          _createElementVNode("td", null, "#" + _toDisplayString(o.operation_id) + " · " + _toDisplayString(o.payload.reference), 1),
          _createElementVNode("td", null, _toDisplayString(o.state) + " · v" + _toDisplayString(o.version), 1),
          _createElementVNode("td", null, _toDisplayString(o.validation.issues.map(i=>i.message).join('; ')||'Consistente'), 1),
          _createElementVNode("td", null, [_createElementVNode("button", { onClick: $event => (openOperation(o.operation_id)) }, "Abrir ficha", 8, ["onClick"])])
        ]))
      }), 256))])])])], 512), [[_vShow, page==='reconciliation']]),
      _withDirectives(_createElementVNode("section", { class: "card" }, [
        _createElementVNode("h1", null, "Financeiro"),
        _createElementVNode("p", null, "Títulos reconhecidos nas operações e títulos preservados do histórico. Cada liquidação usa a mesma escrituração, com partidas próprias; pagar não reconhece novamente o documento."),
        (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(titles, (t) => {
          return (_openBlock(), _createElementBlock("div", { class: "inset" }, [
            _createElementVNode("h3", null, _toDisplayString(t.direction==='pagar'?'A pagar':'A receber') + " · " + _toDisplayString(t.reference), 1),
            _createElementVNode("p", null, [_createTextVNode(_toDisplayString(t.counterparty) + " · vencimento " + _toDisplayString(t.due_date) + " · valor " + _toDisplayString(t.amount) + " · saldo ", 1), _createElementVNode("b", null, _toDisplayString(t.balance), 1)]),
            _createVNode(_component_data_table, {
              rows: t.settlements,
              columns: {paid_date:'Data',reference:'Baixa',amount:'Valor',reversed_at:'Estornado em'}
            }, null, 8, ["rows", "columns"]),
            _createElementVNode("button", {
              onClick: $event => (selectTitle(t)),
              disabled: busy||t.balance==='0.00'||t.canceled_at
            }, "Preparar liquidação", 8, ["onClick", "disabled"])
          ]))
        }), 256)),
        settlementTitle
          ? (_openBlock(), _createElementBlock("form", {
              key: 0,
              onSubmit: _withModifiers(prepareSettlement, ["prevent"]),
              class: "grid"
            }, [
              _createElementVNode("h2", null, "Liquidar " + _toDisplayString(settlementTitle.reference), 1),
              _createElementVNode("label", null, [_createTextVNode("Política"), _withDirectives(_createElementVNode("select", {
                "aria-label": "Política",
                "onUpdate:modelValue": $event => ((settlement.policy_id) = $event),
                required: ""
              }, [_createElementVNode("option", { value: "" }, "Selecione"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(settlementPolicies, (p) => {
                return (_openBlock(), _createElementBlock("option", { value: p.id }, _toDisplayString(p.label), 9, ["value"]))
              }), 256))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, settlement.policy_id]])]),
              _createElementVNode("label", null, [_createTextVNode("Valor"), _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": $event => ((settlement.amount) = $event),
                required: "",
                inputmode: "decimal"
              }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, settlement.amount]])]),
              _createElementVNode("label", null, [_createTextVNode("Data"), _withDirectives(_createElementVNode("input", {
                type: "date",
                "onUpdate:modelValue": $event => ((settlement.paid_date) = $event),
                required: ""
              }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, settlement.paid_date]])]),
              _createElementVNode("label", null, [_createTextVNode("Referência"), _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": $event => ((settlement.reference) = $event),
                required: ""
              }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, settlement.reference]])]),
              _createElementVNode("button", { disabled: busy }, "Abrir ficha da liquidação", 8, ["disabled"])
            ], 40, ["onSubmit"]))
          : _createCommentVNode("", true)
      ], 512), [[_vShow, page==='finance']]),
      _withDirectives(_createElementVNode("section", { class: "card" }, [
        _createElementVNode("h1", null, "Livros e relatórios"),
        books
          ? (_openBlock(), _createElementBlock("p", { key: 0 }, _toDisplayString(books.opening_declared?'Saldos iniciais declarados em '+books.opening_competence:'Saldos iniciais ainda não declarados: os saldos exibidos abrangem apenas movimentos conhecidos.') + " Convenção dos saldos: débitos menos créditos.", 1))
          : _createCommentVNode("", true),
        _createElementVNode("div", { class: "toolbar" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(bookTypes, (b) => {
          return (_openBlock(), _createElementBlock("button", {
            onClick: $event => (bookType=b.id),
            class: _normalizeClass({active:bookType===b.id})
          }, _toDisplayString(b.label), 11, ["onClick"]))
        }), 256))]),
        _createVNode(_component_data_table, {
          rows: books?.[bookType]||[],
          columns: bookColumns
        }, null, 8, ["rows", "columns"]),
        books
          ? (_openBlock(), _createElementBlock("p", { key: 1 }, "Débitos " + _toDisplayString(books.totals.debit) + " · créditos " + _toDisplayString(books.totals.credit), 1))
          : _createCommentVNode("", true),
        _createElementVNode("form", {
          onSubmit: _withModifiers(exportBooks, ["prevent"]),
          class: "grid"
        }, [_createElementVNode("label", null, [_createTextVNode("Motivo da exportação"), _withDirectives(_createElementVNode("input", {
          "onUpdate:modelValue": $event => ((exportReason) = $event),
          required: ""
        }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, exportReason]])]), _createElementVNode("button", { disabled: busy||!books }, "Conferir e preservar exportação operacional", 8, ["disabled"])], 40, ["onSubmit"]),
        _createElementVNode("p", null, "Pacote local com diário, razão, balancete, livro fiscal, financeiro e manifesto de integridade. Adaptadores Prosoft e geração de obrigações SPED dependem de perfis verificados; indisponíveis nesta entrega."),
        (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(exports, (e) => {
          return (_openBlock(), _createElementBlock("article", { class: "inset" }, [_createElementVNode("b", null, "Exportação #" + _toDisplayString(e.id), 1), _createElementVNode("small", null, _toDisplayString(e.created_at) + " · " + _toDisplayString(e.reason), 1), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(e.files, (f) => {
            return (_openBlock(), _createElementBlock("a", {
              href: download('work-export-file',{export_id:e.id,name:f.name}),
              onClick: _withModifiers($event => (downloadFile('work-export-file',{export_id:e.id,name:f.name},f.name)), ["prevent"])
            }, _toDisplayString(f.name), 9, ["href", "onClick"]))
          }), 256))]))
        }), 256))
      ], 512), [[_vShow, page==='books']]),
      _withDirectives(_createElementVNode("section", { class: "card" }, [
        _createElementVNode("h1", null, "Encerramento da competência"),
        _createElementVNode("p", null, "Encerre depois de resolver documentos e versões pendentes e declarar a abertura. A reabertura mantém o histórico e exige motivo."),
        _createVNode(_component_data_table, {
          rows: overview?[overview.counts]:[],
          columns: {pending_documents:'Documentos pendentes',drafts:'Rascunhos',reviewed:'Conferidos não escriturados',posted:'Escriturados',rejected_inputs:'Origens rejeitadas'}
        }, null, 8, ["rows", "columns"]),
        _createElementVNode("form", { onSubmit: _withModifiers(closeCycle, ["prevent"]) }, [_createElementVNode("label", null, [_createTextVNode("Motivo"), _withDirectives(_createElementVNode("input", {
          "onUpdate:modelValue": $event => ((closing.reason) = $event),
          required: ""
        }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, closing.reason]])]), _createElementVNode("label", null, [_withDirectives(_createElementVNode("input", {
          type: "checkbox",
          "onUpdate:modelValue": $event => ((closing.acknowledge_errors) = $event)
        }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, closing.acknowledge_errors]]), _createTextVNode(" Conferi e reconheço os arquivos rejeitados do recorte")]), _createElementVNode("button", { disabled: busy||!cycle }, _toDisplayString(cycle?.state==='encerrada'?'Reabrir com motivo':'Encerrar competência'), 9, ["disabled"])], 40, ["onSubmit"])
      ], 512), [[_vShow, page==='closing']]),
      _withDirectives(_createElementVNode("section", { class: "card" }, [
        _createElementVNode("h1", null, "Histórico preservado e migração"),
        _createElementVNode("p", null, "Registros do processo anterior permanecem consultáveis. Movimentos fechados integram os livros sem serem recriados. Rascunhos retomáveis abrem uma operação para nova conferência."),
        (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(overview?.legacy||[], (r) => {
          return (_openBlock(), _createElementBlock("article", { class: "inset" }, [
            _createElementVNode("h3", null, _toDisplayString(r.kind) + " #" + _toDisplayString(r.id) + " · " + _toDisplayString(r.state), 1),
            _createElementVNode("details", null, [_createElementVNode("summary", null, "Snapshot preservado"), _createElementVNode("pre", null, _toDisplayString(JSON.stringify(r.snapshot,null,2)), 1)]),
            (r.can_resume)
              ? (_openBlock(), _createElementBlock("label", { key: 0 }, [_createTextVNode("Motivo"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((legacyReason) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, legacyReason]])]))
              : _createCommentVNode("", true),
            (r.can_resume)
              ? (_openBlock(), _createElementBlock("button", {
                  key: 1,
                  onClick: $event => (resume(r)),
                  disabled: busy
                }, "Retomar como operação", 8, ["onClick", "disabled"]))
              : _createCommentVNode("", true),
            (r.operation_id)
              ? (_openBlock(), _createElementBlock("button", {
                  key: 2,
                  onClick: $event => (openOperation(r.operation_id))
                }, "Consultar operação vinculada", 8, ["onClick"]))
              : _createCommentVNode("", true)
          ]))
        }), 256)),
        _createElementVNode("h2", null, "Auditoria"),
        _createVNode(_component_data_table, {
          rows: audit,
          columns: {created_at:'Data',actor:'Responsável',action:'Ação',details:'Evidência'}
        }, null, 8, ["rows", "columns"])
      ], 512), [[_vShow, page==='history']]),
      (!company)
        ? (_openBlock(), _createElementBlock("p", {
            key: 3,
            class: "empty"
          }, "Selecione ou cadastre uma empresa no portal para iniciar."))
        : (!cycle && !['imports','setup','chart'].includes(page))
          ? (_openBlock(), _createElementBlock("p", {
              key: 4,
              class: "empty"
            }, "Defina uma competência em Competências. A caixa de entrada já recebe arquivos."))
          : _createCommentVNode("", true)
    ], 8, ["aria-busy"]))
  }
};
