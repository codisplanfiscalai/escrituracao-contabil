/* Template pré-compilado: não requer eval no navegador. */
var _Vue=Vue; var WorkRender=function render(_ctx, _cache) {
  with (_ctx) {
    const { createElementVNode: _createElementVNode, renderList: _renderList, Fragment: _Fragment, openBlock: _openBlock, createElementBlock: _createElementBlock, toDisplayString: _toDisplayString, vModelSelect: _vModelSelect, withDirectives: _withDirectives, createTextVNode: _createTextVNode, createCommentVNode: _createCommentVNode, normalizeClass: _normalizeClass, vModelText: _vModelText, withModifiers: _withModifiers, resolveComponent: _resolveComponent, createVNode: _createVNode, vShow: _vShow, vModelCheckbox: _vModelCheckbox, createBlock: _createBlock } = _Vue

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
      (!embedded)
        ? (_openBlock(), _createElementBlock("nav", {
            key: 0,
            class: "resource-tabs",
            "aria-label": "Guias de recursos"
          }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(resourceTabs, (id) => {
            return (_openBlock(), _createElementBlock("div", {
              key: id,
              class: _normalizeClass({active:page===id})
            }, [_createElementVNode("button", {
              onClick: $event => (navigate(id)),
              "aria-current": page===id?'page':undefined
            }, _toDisplayString(resources.find(r=>r.id===id)?.label), 9, ["onClick", "aria-current"]), _createElementVNode("button", {
              onClick: $event => (closeResource(id)),
              "aria-label": 'Fechar recurso '+resources.find(r=>r.id===id)?.label
            }, "×", 8, ["onClick", "aria-label"])], 2))
          }), 128))]))
        : _createCommentVNode("", true),
      error
        ? (_openBlock(), _createElementBlock("p", {
            key: 1,
            class: "alert error",
            role: "alert"
          }, _toDisplayString(error), 1))
        : _createCommentVNode("", true),
      notice
        ? (_openBlock(), _createElementBlock("p", {
            key: 2,
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
        _createElementVNode("form", {
          onSubmit: _withModifiers(searchSources, ["prevent"]),
          class: "toolbar source-search"
        }, [
          _createElementVNode("label", null, [_createTextVNode("Buscar fontes"), _withDirectives(_createElementVNode("input", {
            "onUpdate:modelValue": $event => ((sourceSearch.query) = $event),
            placeholder: "Arquivo, chave, número ou CPF/CNPJ",
            maxlength: "100"
          }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, sourceSearch.query]])]),
          _createElementVNode("label", null, [_createTextVNode("Tipo da fonte"), _withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((sourceSearch.kind) = $event) }, [_createElementVNode("option", { value: "" }, "Todos"), _createElementVNode("option", null, "XML"), _createElementVNode("option", null, "SPED")], 8, ["onUpdate:modelValue"]), [[_vModelSelect, sourceSearch.kind]])]),
          _createElementVNode("label", null, [_createTextVNode("Direção identificada"), _withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((sourceSearch.direction) = $event) }, [_createElementVNode("option", { value: "" }, "Todas"), _createElementVNode("option", { value: "entrada" }, "Entradas"), _createElementVNode("option", { value: "saida" }, "Saídas")], 8, ["onUpdate:modelValue"]), [[_vModelSelect, sourceSearch.direction]])]),
          _createElementVNode("label", null, [_createTextVNode("Emissão inicial"), _withDirectives(_createElementVNode("input", {
            type: "date",
            "onUpdate:modelValue": $event => ((sourceSearch.issued_from) = $event)
          }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, sourceSearch.issued_from]])]),
          _createElementVNode("label", null, [_createTextVNode("Emissão final"), _withDirectives(_createElementVNode("input", {
            type: "date",
            "onUpdate:modelValue": $event => ((sourceSearch.issued_to) = $event)
          }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, sourceSearch.issued_to]])]),
          _createElementVNode("button", { disabled: busy||!company }, "Buscar sem competência", 8, ["disabled"])
        ], 40, ["onSubmit"]),
        _createElementVNode("p", null, "Busca nas fontes já recebidas deste cliente, sem abertura de competência. Fontes sem emissão identificada não aparecem no filtro por data; direção depende do CNPJ cadastrado."),
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
              _createElementVNode("button", {
                onClick: $event => (showSourceHistory(s)),
                disabled: busy
              }, "Decisões e versões", 8, ["onClick", "disabled"]),
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
                    onClick: $event => (showImpact(s)),
                    disabled: busy
                  }, "Dependências / retirada", 8, ["onClick", "disabled"]))
                : _createCommentVNode("", true)
            ])
          ]))
        }), 128))])])]),
        (sourceTabs.some(t=>!t.closed))
          ? (_openBlock(), _createElementBlock("nav", {
              key: 0,
              class: "source-tabs",
              "aria-label": "Guias de fontes"
            }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(sourceTabs.filter(t=>!t.closed), (t) => {
              return (_openBlock(), _createElementBlock("div", {
                key: t.id,
                class: _normalizeClass({active:activeSourceTab===t.id})
              }, [_createElementVNode("button", {
                onClick: $event => (activeSourceTab=t.id),
                "aria-current": activeSourceTab===t.id?'page':undefined
              }, _toDisplayString(t.kind==='history'?'Decisões':'Dependências') + " · " + _toDisplayString(t.filename), 9, ["onClick", "aria-current"]), _createElementVNode("button", {
                onClick: $event => (closeSourceTab(t)),
                "aria-label": 'Fechar '+(t.kind==='history'?'decisões':'dependências')+' de '+t.filename
              }, "×", 8, ["onClick", "aria-label"])], 2))
            }), 128))]))
          : _createCommentVNode("", true),
        (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(sourceTabs, (t) => {
          return _withDirectives((_openBlock(), _createElementBlock("article", {
            key: t.id,
            class: "inset source-guide",
            "data-source-guide": t.id
          }, [_createElementVNode("button", {
            onClick: $event => (refreshSourceTab(t)),
            disabled: busy
          }, "Atualizar consulta", 8, ["onClick", "disabled"]), (t.kind==='history')
            ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [_createElementVNode("h2", null, "Decisões · " + _toDisplayString(t.filename), 1), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(t.data, (r) => {
                return (_openBlock(), _createElementBlock("details", null, [_createElementVNode("summary", null, "Versão " + _toDisplayString(r.version) + " · " + _toDisplayString(r.evidence.state) + " · " + _toDisplayString(r.reason), 1), _createElementVNode("small", null, _toDisplayString(r.created_at) + " · responsável " + _toDisplayString(r.actor), 1), _createElementVNode("pre", null, _toDisplayString(JSON.stringify(r.evidence,null,2)), 1)]))
              }), 256))], 64))
            : (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [
                _createElementVNode("h2", null, "Consequências da retirada · " + _toDisplayString(t.filename), 1),
                _createElementVNode("pre", null, _toDisplayString(JSON.stringify(t.data,null,2)), 1),
                _createElementVNode("label", null, [_createTextVNode("Motivo da retirada desta fonte"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((t.reason) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, t.reason]])]),
                _createElementVNode("label", null, [_withDirectives(_createElementVNode("input", {
                  type: "checkbox",
                  "onUpdate:modelValue": $event => ((t.confirmed) = $event)
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, t.confirmed]]), _createTextVNode(" Conferi as dependências e confirmo a retirada lógica")]),
                _createElementVNode("button", {
                  onClick: $event => (removeSource(t)),
                  disabled: busy||!t.confirmed||t.data.protected.length
                }, "Confirmar retirada preservando original", 8, ["onClick", "disabled"])
              ], 64))], 8, ["data-source-guide"])), [[_vShow, !t.closed && activeSourceTab===t.id]])
        }), 128))
      ], 512), [[_vShow, page==='imports']]),
      _withDirectives(_createElementVNode("section", { class: "card" }, [
        _createElementVNode("h1", null, "Escrituração"),
        _createElementVNode("p", null, "Importe documentos ou registre manualmente. Confira fatos fiscais, partidas e cobrança na mesma operação; a efetivação gera movimentos e títulos juntos."),
        _createElementVNode("details", { class: "inset" }, [
          _createElementVNode("summary", null, "Preparar operações dos documentos organizados"),
          _createElementVNode("p", null, "Escolha documentos, natureza, política aprovada e data. A prévia não efetiva movimentos. A confirmação cria somente rascunhos, com os originais e os valores observados preservados."),
          _createElementVNode("button", {
            type: "button",
            onClick: selectPreparationVisible,
            disabled: busy||!preparationCandidates.length
          }, "Selecionar documentos visíveis para preparar", 8, ["onClick", "disabled"]),
          _createElementVNode("p", null, _toDisplayString(preparationSelected.length) + " selecionados; até 50 documentos visíveis sem operação.", 1),
          _createElementVNode("div", { class: "table-scroll" }, [_createElementVNode("table", null, [_createElementVNode("thead", null, [_createElementVNode("tr", null, [_createElementVNode("th", null, "Selecionar"), _createElementVNode("th", null, "Documento"), _createElementVNode("th", null, "Origem")])]), _createElementVNode("tbody", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(preparationCandidates, (doc) => {
            return (_openBlock(), _createElementBlock("tr", { key: doc.id }, [_createElementVNode("td", null, [_createElementVNode("label", null, [_withDirectives(_createElementVNode("input", {
              type: "checkbox",
              "aria-label": 'Preparar documento '+doc.id,
              value: doc.id,
              "onUpdate:modelValue": $event => ((preparationSelected) = $event),
              disabled: busy,
              onChange: $event => {preparationPreview=null;preparationConfirmed=false}
            }, null, 40, ["aria-label", "value", "onUpdate:modelValue", "disabled", "onChange"]), [[_vModelCheckbox, preparationSelected]]), _createTextVNode(" Incluir")])]), _createElementVNode("td", null, _toDisplayString(doc.number) + " · " + _toDisplayString(doc.model) + " · " + _toDisplayString(doc.total), 1), _createElementVNode("td", null, [_withDirectives(_createElementVNode("select", {
              "aria-label": 'Origem do documento '+doc.id,
              "onUpdate:modelValue": $event => ((preparationSources[doc.id]) = $event),
              disabled: busy,
              onChange: $event => {preparationPreview=null;preparationConfirmed=false}
            }, [_createElementVNode("option", { value: "" }, _toDisplayString(doc.source.observations.length===1?'Única origem, sujeita à conferência':'Selecione uma origem'), 1), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(doc.source.observations, (source) => {
              return (_openBlock(), _createElementBlock("option", { value: String(source.id) }, "#" + _toDisplayString(source.id) + " · arquivo " + _toDisplayString(source.file_id) + " · " + _toDisplayString(source.profile), 9, ["value"]))
            }), 256))], 40, ["aria-label", "onUpdate:modelValue", "disabled", "onChange"]), [[_vModelSelect, preparationSources[doc.id]]])])]))
          }), 128))])])]),
          _createElementVNode("form", {
            onSubmit: _withModifiers(previewPreparation, ["prevent"]),
            onInput: $event => {preparationPreview=null;preparationConfirmed=false}
          }, [_createElementVNode("div", { class: "grid" }, [
            _createElementVNode("label", null, [_createTextVNode("Natureza da preparação"), _withDirectives(_createElementVNode("select", {
              "aria-label": "Natureza da preparação",
              "onUpdate:modelValue": $event => ((preparationConfig.operation) = $event),
              onChange: $event => (preparationConfig.policy_id=''),
              required: ""
            }, [_createElementVNode("option", { value: "" }, "Selecione explicitamente"), _createElementVNode("option", { value: "entrada" }, "Entrada"), _createElementVNode("option", { value: "saida" }, "Saída")], 40, ["onUpdate:modelValue", "onChange"]), [[_vModelSelect, preparationConfig.operation]])]),
            _createElementVNode("label", null, [_createTextVNode("Política da preparação"), _withDirectives(_createElementVNode("select", {
              "aria-label": "Política da preparação",
              "onUpdate:modelValue": $event => ((preparationConfig.policy_id) = $event),
              required: ""
            }, [_createElementVNode("option", { value: "" }, "Selecione política aprovada"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(preparationPolicies, (policy) => {
              return (_openBlock(), _createElementBlock("option", { value: String(policy.id) }, _toDisplayString(policy.label) + " · v" + _toDisplayString(policy.version), 9, ["value"]))
            }), 256))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, preparationConfig.policy_id]])]),
            _createElementVNode("label", null, [_createTextVNode("Data de escrituração dos documentos"), _withDirectives(_createElementVNode("input", {
              type: "date",
              "onUpdate:modelValue": $event => ((preparationConfig.posting_date) = $event),
              required: ""
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, preparationConfig.posting_date]])]),
            _createElementVNode("label", null, [_createTextVNode("Modo dos itens na preparação"), _createElementVNode("select", {
              "aria-label": "Modo dos itens na preparação",
              value: preparationConfig.item_mode,
              onChange: $event => (setPreparationMode($event.target.value)),
              required: ""
            }, [
              _createElementVNode("option", { value: "" }, "Selecione explicitamente"),
              _createElementVNode("option", { value: "cabecalho" }, "Cabeçalho, sem extração dos itens"),
              _createElementVNode("option", { value: "observar_xml" }, "Observar valores XML, sem propor itens tributários"),
              _createElementVNode("option", { value: "propor_itens_xml" }, "Propor itens com escolhas de cópia conferidas")
            ], 40, ["value", "onChange"])]),
            (preparationConfig.item_mode==='propor_itens_xml')
              ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [_createElementVNode("label", null, [_createTextVNode("Total atribuído aos itens"), _withDirectives(_createElementVNode("select", {
                  "aria-label": "Total atribuído aos itens",
                  "onUpdate:modelValue": $event => ((preparationConfig.total_source) = $event)
                }, [_createElementVNode("option", { value: "nao_copiar" }, "Deixar em branco para declarar depois"), _createElementVNode("option", { value: "vProd" }, "Copiar vProd, sem presumir total líquido")], 8, ["onUpdate:modelValue"]), [[_vModelSelect, preparationConfig.total_source]])]), _createElementVNode("fieldset", null, [_createElementVNode("legend", null, "Bases observadas a copiar explicitamente"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(['icms_base','st_base','fcp_base','pis_base','cofins_base'], (base) => {
                  return (_openBlock(), _createElementBlock("label", null, [_withDirectives(_createElementVNode("input", {
                    type: "checkbox",
                    value: base,
                    "onUpdate:modelValue": $event => ((preparationConfig.copy_bases) = $event)
                  }, null, 8, ["value", "onUpdate:modelValue"]), [[_vModelCheckbox, preparationConfig.copy_bases]]), _createTextVNode(" " + _toDisplayString(base), 1)]))
                }), 256))])], 64))
              : _createCommentVNode("", true)
          ]), _createElementVNode("p", null, "CFOP observado não é convertido em CFOP da empresa. Componentes, tratamentos e direito a crédito não são definidos por esta preparação. Ausências não viram zero."), _createElementVNode("button", { disabled: busy||!preparationSelected.length }, "Gerar prévia da preparação", 8, ["disabled"])], 40, ["onSubmit", "onInput"]),
          preparationPreview
            ? (_openBlock(), _createElementBlock("article", {
                key: 0,
                class: "inset"
              }, [
                _createElementVNode("h3", null, "Prévia da preparação dos documentos"),
                _createElementVNode("p", null, _toDisplayString(preparationPreview.snapshot.ready?'Rascunhos podem ser preparados após conferência.':'Há pendências; nenhum documento será preparado.'), 1),
                (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(preparationPreview.snapshot.items, (item) => {
                  return (_openBlock(), _createElementBlock("article", {
                    class: "inset",
                    key: item.document_id
                  }, [
                    _createElementVNode("b", null, "Documento #" + _toDisplayString(item.document_id), 1),
                    (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(item.blockers, (blocker) => {
                      return (_openBlock(), _createElementBlock("p", { class: "error" }, _toDisplayString(blocker), 1))
                    }), 256)),
                    (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(item.warnings, (warning) => {
                      return (_openBlock(), _createElementBlock("p", null, _toDisplayString(warning), 1))
                    }), 256)),
                    (item.payload)
                      ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [_createElementVNode("p", null, _toDisplayString(item.payload.fiscal.operation) + " · " + _toDisplayString(item.payload.fiscal.posting_date) + " · total documental " + _toDisplayString(item.payload.fiscal.total), 1), (item.payload.xml_item_evidence)
                          ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [_createVNode(_component_data_table, {
                              rows: xmlObservedRows(item.payload.xml_item_evidence),
                              columns: {item:'nItem',locator:'Localizador',cfop:'CFOP observado',vProd:'vProd observado',vFrete:'Frete',vSeg:'Seguro',vDesc:'Desconto',vOutro:'Outros',issues:'Críticas',unhandled:'Não extraído'}
                            }, null, 8, ["rows", "columns"]), _createElementVNode("button", {
                              type: "button",
                              onClick: $event => (preparationInspect=item.payload.xml_item_evidence)
                            }, "Inspecionar caminhos do documento " + _toDisplayString(item.document_id), 9, ["onClick"])], 64))
                          : _createCommentVNode("", true)], 64))
                      : _createCommentVNode("", true)
                  ]))
                }), 128)),
                preparationInspect
                  ? (_openBlock(), _createElementBlock("pre", { key: 0 }, _toDisplayString(JSON.stringify(preparationInspect,null,2)), 1))
                  : _createCommentVNode("", true),
                _createElementVNode("label", null, [_createTextVNode("Motivo da preparação dos documentos"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((preparationReason) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, preparationReason]])]),
                _createElementVNode("label", null, [_createTextVNode("Referência da conferência da preparação"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((preparationReview) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, preparationReview]])]),
                _createElementVNode("label", null, [_withDirectives(_createElementVNode("input", {
                  type: "checkbox",
                  "onUpdate:modelValue": $event => ((preparationConfirmed) = $event)
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, preparationConfirmed]]), _createTextVNode(" Conferi documentos, origens, política, data e cópias; autorizo somente criar rascunhos")]),
                _createElementVNode("button", {
                  type: "button",
                  onClick: applyPreparation,
                  disabled: busy||!preparationPreview.snapshot.ready||!preparationConfirmed
                }, "Criar rascunhos da prévia", 8, ["onClick", "disabled"])
              ]))
            : _createCommentVNode("", true),
          _createElementVNode("button", {
            type: "button",
            onClick: loadPreparations,
            disabled: busy||!cycle
          }, "Consultar últimas 50 preparações", 8, ["onClick", "disabled"]),
          (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(preparationHistory, (row) => {
            return (_openBlock(), _createElementBlock("article", {
              key: row.id,
              class: "inset"
            }, [_createElementVNode("b", null, "Preparação #" + _toDisplayString(row.id) + " · " + _toDisplayString(row.reason), 1), _createElementVNode("button", {
              type: "button",
              onClick: $event => (openPreparation(row))
            }, "Abrir preparação " + _toDisplayString(row.id), 9, ["onClick"])]))
          }), 128)),
          preparationReceipt
            ? (_openBlock(), _createElementBlock("article", {
                key: 1,
                class: "inset"
              }, [_createElementVNode("h3", null, "Manifesto da preparação #" + _toDisplayString(preparationReceipt.id), 1), _createVNode(_component_data_table, {
                rows: preparationReceipt.snapshot.items,
                columns: {document_id:'Documento',operation_id:'Operação criada',version:'Versão',snapshot_hash:'Hash',warnings:'Conferências pendentes'}
              }, null, 8, ["rows", "columns"]), _createElementVNode("button", {
                type: "button",
                onClick: downloadPreparation
              }, "Baixar preparação e evidências XML", 8, ["onClick"])]))
            : _createCommentVNode("", true)
        ]),
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
            key: 3,
            class: "card operation"
          }, [
            _createElementVNode("header", null, [_createElementVNode("h2", null, _toDisplayString(active.title), 1), _createElementVNode("span", null, _toDisplayString(active.operation?.state||'Rascunho da guia') + " · " + _toDisplayString(active.operation?'v'+active.operation.version:'não efetivado'), 1), _createElementVNode("small", null, _toDisplayString(draftStatus), 1)]),
            _createElementVNode("form", { onSubmit: _withModifiers(saveOperation, ["prevent"]) }, [
              _createElementVNode("fieldset", { disabled: busy||['escriturado','dispensado'].includes(active.operation?.state) }, [
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
                  _createElementVNode("label", null, [_createTextVNode("NCM declarado para regra"), _withDirectives(_createElementVNode("input", {
                    "onUpdate:modelValue": $event => ((active.data.payload.fiscal.ncm) = $event),
                    maxlength: "8"
                  }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, active.data.payload.fiscal.ncm]])]),
                  _createElementVNode("label", null, [_createTextVNode("Código de serviço declarado"), _withDirectives(_createElementVNode("input", {
                    "onUpdate:modelValue": $event => ((active.data.payload.fiscal.service_code) = $event),
                    maxlength: "30"
                  }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, active.data.payload.fiscal.service_code]])]),
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
                  }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, active.data.payload.fiscal.iss_amount]])]),
                  _createElementVNode("label", null, [_createTextVNode("Base PIS informada"), _withDirectives(_createElementVNode("input", {
                    "onUpdate:modelValue": $event => ((active.data.payload.fiscal.pis_base) = $event),
                    inputmode: "decimal"
                  }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, active.data.payload.fiscal.pis_base]])]),
                  _createElementVNode("label", null, [_createTextVNode("PIS informado"), _withDirectives(_createElementVNode("input", {
                    "onUpdate:modelValue": $event => ((active.data.payload.fiscal.pis_amount) = $event),
                    inputmode: "decimal"
                  }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, active.data.payload.fiscal.pis_amount]])]),
                  _createElementVNode("label", null, [_createTextVNode("Base COFINS informada"), _withDirectives(_createElementVNode("input", {
                    "onUpdate:modelValue": $event => ((active.data.payload.fiscal.cofins_base) = $event),
                    inputmode: "decimal"
                  }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, active.data.payload.fiscal.cofins_base]])]),
                  _createElementVNode("label", null, [_createTextVNode("COFINS informado"), _withDirectives(_createElementVNode("input", {
                    "onUpdate:modelValue": $event => ((active.data.payload.fiscal.cofins_amount) = $event),
                    inputmode: "decimal"
                  }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, active.data.payload.fiscal.cofins_amount]])])
                ]), _createElementVNode("p", null, "Valores informados pelo operador ou pela origem. Regras aprovadas podem calcular tributos na versão salva; não há homologação de obrigação fiscal. NCM e serviço são escopos declarados para a regra. O modo por item exige componentes, bases e vínculos conferidos; não classifica produtos automaticamente.")], 8, ["open"]),
                (active.data.payload.xml_item_evidence)
                  ? (_openBlock(), _createElementBlock("details", { key: 0 }, [
                      _createElementVNode("summary", null, "Valores observados do XML da ficha"),
                      _createElementVNode("p", null, "Referência da origem; os valores usados na escrituração são declarados/conferidos nos campos próprios. Nenhum enquadramento é inferido."),
                      _createVNode(_component_data_table, {
                        rows: xmlObservedRows(active.data.payload.xml_item_evidence),
                        columns: {item:'nItem',locator:'Localizador',cfop:'CFOP observado',vProd:'vProd observado',vFrete:'Frete',vSeg:'Seguro',vDesc:'Desconto',vOutro:'Outros',issues:'Críticas',unhandled:'Não extraído'}
                      }, null, 8, ["rows", "columns"]),
                      _createElementVNode("details", null, [_createElementVNode("summary", null, "Caminhos e evidência preservada"), _createElementVNode("pre", null, _toDisplayString(JSON.stringify(active.data.payload.xml_item_evidence,null,2)), 1)])
                    ]))
                  : _createCommentVNode("", true),
                _createElementVNode("details", {
                  class: "tax-items",
                  open: !!active.data.payload.tax_items
                }, [
                  _createElementVNode("summary", null, "Tributação por item e tratamentos mistos"),
                  _createElementVNode("p", null, "Informe o total líquido atribuído a cada item, incluindo os rateios conferidos. A soma deve conferir com o documento. Bases, reduções, retenções, ST e DIFAL dependem de regras aprovadas; valores não são extraídos automaticamente da lista de produtos."),
                  _createElementVNode("div", { class: "toolbar" }, [_createElementVNode("button", {
                    type: "button",
                    onClick: addTaxItem
                  }, "Adicionar item tributário", 8, ["onClick"]), _createElementVNode("button", {
                    type: "button",
                    onClick: proposeSourceTaxItems,
                    disabled: !active.data.payload.document_id
                  }, "Propor vínculos dos itens da fonte", 8, ["onClick", "disabled"]), _createElementVNode("button", {
                    type: "button",
                    onClick: useDocumentTaxMode,
                    disabled: !active.data.payload.tax_items
                  }, "Usar tributação documental", 8, ["onClick", "disabled"])]),
                  (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(active.data.payload.tax_items, (item, index) => {
                    return (_openBlock(), _createElementBlock("article", {
                      class: "inset",
                      key: item.id,
                      "data-tax-item": index
                    }, [_createElementVNode("h3", null, "Item " + _toDisplayString(index+1), 1), _createElementVNode("div", { class: "grid" }, [
                      _createElementVNode("label", null, [_createTextVNode("Descrição do item"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((item.description) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, item.description]])]),
                      _createElementVNode("label", null, [_createTextVNode("Total líquido atribuído ao item"), _withDirectives(_createElementVNode("input", {
                        "onUpdate:modelValue": $event => ((item.values.total) = $event),
                        inputmode: "decimal"
                      }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, item.values.total]])]),
                      _createElementVNode("label", null, [_createTextVNode("CFOP do item"), _withDirectives(_createElementVNode("input", {
                        "onUpdate:modelValue": $event => ((item.cfop) = $event),
                        maxlength: "4"
                      }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, item.cfop]])]),
                      _createElementVNode("label", null, [_createTextVNode("NCM do item"), _withDirectives(_createElementVNode("input", {
                        "onUpdate:modelValue": $event => ((item.ncm) = $event),
                        maxlength: "8"
                      }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, item.ncm]])]),
                      _createElementVNode("label", null, [_createTextVNode("Serviço do item"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((item.service_code) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, item.service_code]])]),
                      _createElementVNode("label", null, [_createTextVNode("Tratamento declarado do item"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((item.treatment) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, item.treatment]])]),
                      _createElementVNode("label", null, [_createTextVNode("Origem e conferência dos valores do item"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((item.source_reference) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, item.source_reference]])]),
                      _createElementVNode("label", null, [_createTextVNode("Localizador na fonte"), _withDirectives(_createElementVNode("input", {
                        "onUpdate:modelValue": $event => ((item.source_locator) = $event),
                        placeholder: "Preenchido pela proposta da fonte"
                      }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, item.source_locator]])]),
                      _createElementVNode("label", null, [_createTextVNode("Componentes a calcular"), _createElementVNode("input", {
                        value: item.taxes.join(', '),
                        onChange: $event => (itemTaxList(item,$event.target.value)),
                        placeholder: "ICMS, FCP:CODIGO, ICMS_ST, ICMS_DIFAL, RETENCAO:CODIGO"
                      }, null, 40, ["value", "onChange"])]),
                      _createElementVNode("label", null, [_createTextVNode("Motivo quando não houver componentes"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((item.no_tax_reason) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, item.no_tax_reason]])]),
                      (_openBlock(true), _createElementBlock(_Fragment, null, _renderList([['icms_base','Base ICMS do item'],['iss_base','Base ISS do item'],['pis_base','Base PIS do item'],['cofins_base','Base COFINS do item'],['st_base','Base ST declarada do item'],['difal_base','Base DIFAL declarada do item'],['retention_base','Base de retenção do item'],['fcp_base','Base FCP declarada do item'],['net_base','Base líquida sem componentes do grupo'],['st_deduction','Dedução própria declarada para ST']], (field) => {
                        return (_openBlock(), _createElementBlock("label", null, [_createElementVNode("span", null, _toDisplayString(field[1]), 1), _withDirectives(_createElementVNode("input", {
                          "onUpdate:modelValue": $event => ((item.values[field[0]]) = $event),
                          inputmode: "decimal"
                        }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, item.values[field[0]]]])]))
                      }), 256))
                    ]), _createElementVNode("button", {
                      type: "button",
                      onClick: $event => (active.data.payload.tax_items.splice(index,1))
                    }, "Remover item tributário", 8, ["onClick"])], 8, ["data-tax-item"]))
                  }), 128)),
                  _createElementVNode("p", null, "Componentes separados por vírgulas. Retenções exigem o identificador definido na regra. Um item sem componentes exige motivo e não pode contrariar uma regra aplicável. Componentes especiais não alteram automaticamente títulos ou partidas.")
                ], 8, ["open"]),
                _createElementVNode("label", null, [_withDirectives(_createElementVNode("input", {
                  type: "checkbox",
                  "onUpdate:modelValue": $event => ((active.data.payload.acknowledge_differences) = $event)
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, active.data.payload.acknowledge_differences]]), _createTextVNode(" Conferi divergências entre as fontes")]),
                (active.data.payload.fiscal.operation==='abertura')
                  ? (_openBlock(), _createElementBlock("label", { key: 1 }, [_withDirectives(_createElementVNode("input", {
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
                  ? (_openBlock(), _createElementBlock("div", { key: 2 }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(active.data.payload.finance.installments, (p, i) => {
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
              ], 8, ["disabled"]),
              (active.data.payload.fiscal.operation==='ajuste')
                ? (_openBlock(), _createElementBlock("details", { key: 0 }, [
                    _createElementVNode("summary", null, "Vínculo de ajuste tributário explícito"),
                    _createElementVNode("label", null, [_createTextVNode("Operação de origem do ajuste tributário"), _withDirectives(_createElementVNode("input", {
                      "onUpdate:modelValue": $event => ((active.data.payload.tax_adjustment_of) = $event),
                      inputmode: "numeric"
                    }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, active.data.payload.tax_adjustment_of]])]),
                    _createElementVNode("label", null, [_createTextVNode("Motivo do ajuste tributário"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((active.data.payload.tax_adjustment_reason) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, active.data.payload.tax_adjustment_reason]])]),
                    _createElementVNode("p", null, "Informe valores e efeito pela regra aprovada. O vínculo não presume reversão legal de créditos ou débitos.")
                  ]))
                : _createCommentVNode("", true),
              _createElementVNode("label", null, [_createTextVNode("Motivo desta ação"), _withDirectives(_createElementVNode("input", {
                id: "operation-reason",
                disabled: busy,
                "onUpdate:modelValue": $event => ((active.data.reason) = $event),
                required: ""
              }, null, 8, ["disabled", "onUpdate:modelValue"]), [[_vModelText, active.data.reason]])]),
              _createElementVNode("div", { class: "toolbar" }, [
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
              ])
            ], 40, ["onSubmit"]),
            _createElementVNode("div", { class: "inset" }, [
              _createElementVNode("h3", null, "Tributação pelas regras da empresa"),
              _createElementVNode("button", {
                onClick: previewTaxes,
                disabled: busy||!active.operation||['escriturado','dispensado'].includes(active.operation?.state)||dirty
              }, "Gerar prévia de tributação", 8, ["onClick", "disabled"]),
              (taxPreview && taxPreview.snapshot.operation_id===active.operation?.operation_id)
                ? (_openBlock(), _createElementBlock("div", { key: 0 }, [
                    (['tributacao-itens-v2','tributacao-itens-v3','tributacao-itens-v4'].includes(taxPreview.snapshot.profile))
                      ? (_openBlock(), _createBlock(_component_data_table, {
                          key: 0,
                          rows: taxPreview.snapshot.lines,
                          columns: {item_id:'Item',component_key:'Componente',base:'Base',rate:'Taxa (%)',amount:'Valor',effect:'Efeito',revenue_code:'Receita'}
                        }, null, 8, ["rows", "columns"]))
                      : _createCommentVNode("", true),
                    (taxPreview.snapshot.grossup_groups?.length)
                      ? (_openBlock(), _createBlock(_component_data_table, {
                          key: 1,
                          rows: taxPreview.snapshot.grossup_groups,
                          columns: {item_id:'Item',components:'Grupo por dentro',declared_net_base:'Base líquida',reduced_net_base:'Líquida reduzida',grossed_base:'Base bruta',rounded_tax_sum:'Tributos',residual:'Diferença',residual_policy:'Política da diferença'}
                        }, null, 8, ["rows", "columns"]))
                      : _createCommentVNode("", true),
                    _createElementVNode("details", { open: !['tributacao-itens-v2','tributacao-itens-v3','tributacao-itens-v4'].includes(taxPreview.snapshot.profile) }, [_createElementVNode("summary", null, "Conferir base, regra, taxa e arredondamento"), _createElementVNode("pre", null, _toDisplayString(JSON.stringify(taxPreview.snapshot,null,2)), 1)], 8, ["open"]),
                    _createElementVNode("button", {
                      onClick: applyTaxes,
                      disabled: busy||dirty
                    }, "Aplicar cálculo em nova versão", 8, ["onClick", "disabled"])
                  ]))
                : _createCommentVNode("", true),
              (active.data.payload.tax_components)
                ? (_openBlock(), _createBlock(_component_data_table, {
                    key: 1,
                    rows: active.data.payload.tax_components,
                    columns: {component_key:'Componente calculado',base:'Base total',amount:'Valor total'}
                  }, null, 8, ["rows", "columns"]))
                : _createCommentVNode("", true),
              (active.data.payload.tax_calculation)
                ? (_openBlock(), _createElementBlock("details", { key: 2 }, [_createElementVNode("summary", null, "Memória de cálculo preservada na operação"), _createElementVNode("pre", null, _toDisplayString(JSON.stringify(active.data.payload.tax_calculation,null,2)), 1)]))
                : _createCommentVNode("", true),
              (active.data.payload.tax_calculation && !['escriturado','dispensado'].includes(active.operation?.state))
                ? (_openBlock(), _createElementBlock("div", { key: 3 }, [_createElementVNode("label", null, [_createTextVNode("Motivo para substituir cálculo automático"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((taxOverrideReason) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, taxOverrideReason]])]), _createElementVNode("button", {
                    onClick: useManualTaxes,
                    disabled: busy
                  }, "Preparar exceção com valores informados", 8, ["onClick", "disabled"])]))
                : _createCommentVNode("", true)
            ]),
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
        _createElementVNode("nav", {
          class: "toolbar book-tabs",
          role: "tablist",
          "aria-label": "Guias dos livros"
        }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(bookTypes, (b) => {
          return (_openBlock(), _createElementBlock("button", {
            id: 'book-tab-'+b.id,
            role: "tab",
            onKeydown: $event => (bookKey($event,b.id)),
            tabindex: bookType===b.id?0:-1,
            "aria-selected": bookType===b.id,
            "aria-controls": 'book-panel-'+b.id,
            onClick: $event => (bookType=b.id),
            class: _normalizeClass({active:bookType===b.id})
          }, _toDisplayString(b.label), 43, ["id", "onKeydown", "tabindex", "aria-selected", "aria-controls", "onClick"]))
        }), 256))]),
        (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(bookTypes, (b) => {
          return _withDirectives((_openBlock(), _createElementBlock("section", {
            key: b.id,
            id: 'book-panel-'+b.id,
            role: "tabpanel",
            "aria-labelledby": 'book-tab-'+b.id
          }, [_createVNode(_component_data_table, {
            rows: books?.[b.id]||[],
            columns: bookColumnsFor(b.id)
          }, null, 8, ["rows", "columns"])], 8, ["id", "aria-labelledby"])), [[_vShow, bookType===b.id]])
        }), 128)),
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
        _createElementVNode("h1", null, "Tributação e apuração"),
        _createElementVNode("p", null, "Parâmetros exclusivos da empresa selecionada. Nenhuma tabela legal ou alíquota foi carregada automaticamente. Códigos isolados não definem tributação. Revise origem, vigência, base, taxa, efeito e arredondamento com o responsável antes de aprovar."),
        _createElementVNode("details", { open: "" }, [
          _createElementVNode("summary", null, "CFOP, NCM, códigos de receita e de serviço"),
          _createElementVNode("form", {
            onSubmit: _withModifiers(saveTaxCode, ["prevent"]),
            class: "grid"
          }, [
            _createElementVNode("label", null, [_createTextVNode("Tabela do código"), _withDirectives(_createElementVNode("select", {
              "aria-label": "Tabela do código",
              "onUpdate:modelValue": $event => ((codeForm.kind) = $event),
              disabled: codeForm.expected_version>0
            }, [
              _createElementVNode("option", { value: "cfop" }, "CFOP"),
              _createElementVNode("option", { value: "ncm" }, "NCM"),
              _createElementVNode("option", { value: "revenue" }, "Receita"),
              _createElementVNode("option", { value: "service" }, "Serviço")
            ], 8, ["onUpdate:modelValue", "disabled"]), [[_vModelSelect, codeForm.kind]])]),
            _createElementVNode("label", null, [_createTextVNode("Código cadastrado"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((codeForm.code) = $event),
              disabled: codeForm.expected_version>0,
              required: "",
              maxlength: "30"
            }, null, 8, ["onUpdate:modelValue", "disabled"]), [[_vModelText, codeForm.code]])]),
            _createElementVNode("label", null, [_createTextVNode("Descrição do código"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((codeForm.data.description) = $event),
              required: "",
              maxlength: "1000"
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, codeForm.data.description]])]),
            _createElementVNode("label", null, [_createTextVNode("Origem e versão da tabela"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((codeForm.data.source_reference) = $event),
              required: "",
              maxlength: "1000"
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, codeForm.data.source_reference]])]),
            _createElementVNode("label", null, [_createTextVNode("Vigência inicial do código"), _withDirectives(_createElementVNode("input", {
              type: "date",
              "onUpdate:modelValue": $event => ((codeForm.data.valid_from) = $event),
              required: ""
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, codeForm.data.valid_from]])]),
            _createElementVNode("label", null, [_createTextVNode("Vigência final do código"), _withDirectives(_createElementVNode("input", {
              type: "date",
              "onUpdate:modelValue": $event => ((codeForm.data.valid_to) = $event)
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, codeForm.data.valid_to]])]),
            _createElementVNode("label", null, [_createTextVNode("Estado do código"), _withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((codeForm.state) = $event) }, [_createElementVNode("option", { value: "ativo" }, "Ativo"), _createElementVNode("option", { value: "inativo" }, "Inativo")], 8, ["onUpdate:modelValue"]), [[_vModelSelect, codeForm.state]])]),
            _createElementVNode("label", null, [_createTextVNode("Motivo do cadastro do código"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((codeForm.reason) = $event),
              required: ""
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, codeForm.reason]])]),
            _createElementVNode("button", { disabled: busy||!company }, "Salvar versão do código", 8, ["disabled"]),
            _createElementVNode("button", {
              type: "button",
              onClick: newTaxCode
            }, "Novo código", 8, ["onClick"])
          ], 40, ["onSubmit"]),
          _createElementVNode("form", {
            onSubmit: _withModifiers($event => (searchTaxCodes(0)), ["prevent"]),
            class: "grid"
          }, [_createElementVNode("label", null, [_createTextVNode("Filtrar tabela cadastrada"), _withDirectives(_createElementVNode("select", {
            "onUpdate:modelValue": $event => ((codeSearch.kind) = $event),
            "aria-label": "Filtrar tabela cadastrada"
          }, [
            _createElementVNode("option", { value: "" }, "Todas"),
            _createElementVNode("option", { value: "cfop" }, "CFOP"),
            _createElementVNode("option", { value: "ncm" }, "NCM"),
            _createElementVNode("option", { value: "revenue" }, "Receita"),
            _createElementVNode("option", { value: "service" }, "Serviço")
          ], 8, ["onUpdate:modelValue"]), [[_vModelSelect, codeSearch.kind]])]), _createElementVNode("label", null, [_createTextVNode("Buscar código cadastrado"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((codeSearch.query) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, codeSearch.query]])]), _createElementVNode("button", { disabled: busy }, "Buscar códigos cadastrados", 8, ["disabled"])], 40, ["onSubmit"]),
          _createElementVNode("p", null, _toDisplayString(taxConfig.catalog_page?.total||0) + " códigos atuais · página de até 100 registros", 1),
          _createElementVNode("div", { class: "toolbar" }, [_createElementVNode("button", {
            onClick: $event => (searchTaxCodes(Math.max(0,(taxConfig.catalog_page?.offset||0)-100))),
            disabled: busy||!taxConfig.catalog_page?.offset
          }, "Códigos anteriores", 8, ["onClick", "disabled"]), _createElementVNode("button", {
            onClick: $event => (searchTaxCodes((taxConfig.catalog_page?.offset||0)+100)),
            disabled: busy||(taxConfig.catalog_page?.offset||0)+100>=(taxConfig.catalog_page?.total||0)
          }, "Próximos códigos", 8, ["onClick", "disabled"])]),
          (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(latestTaxCodes, (row) => {
            return (_openBlock(), _createElementBlock("article", {
              key: row.id,
              class: "inset"
            }, [
              _createElementVNode("b", null, _toDisplayString(row.kind) + " · " + _toDisplayString(row.code) + " · v" + _toDisplayString(row.version) + " · " + _toDisplayString(row.state), 1),
              _createElementVNode("p", null, _toDisplayString(row.data.description) + " · " + _toDisplayString(row.data.valid_from) + " a " + _toDisplayString(row.data.valid_to||'sem término informado'), 1),
              _createElementVNode("p", null, "Origem: " + _toDisplayString(row.data.source_reference), 1),
              _createElementVNode("button", { onClick: $event => (editTaxCode(row)) }, "Editar código", 8, ["onClick"]),
              _createElementVNode("button", { onClick: $event => (showTaxCodeHistory(row)) }, "Histórico do código", 8, ["onClick"])
            ]))
          }), 128)),
          codeHistory
            ? (_openBlock(), _createElementBlock("details", {
                key: 0,
                open: ""
              }, [
                _createElementVNode("summary", null, "Histórico " + _toDisplayString(codeHistory.kind) + " · " + _toDisplayString(codeHistory.code) + " · " + _toDisplayString(codeHistory.total) + " versões", 1),
                _createVNode(_component_data_table, {
                  rows: codeHistory.items,
                  columns: {version:'Versão',state:'Estado',data:'Dados e origem',actor:'Responsável',reason:'Motivo',created_at:'Data'}
                }, null, 8, ["rows", "columns"]),
                _createElementVNode("button", {
                  onClick: $event => (showTaxCodeHistory(codeHistory,Math.max(0,codeHistory.offset-100))),
                  disabled: busy||!codeHistory.offset
                }, "Versões anteriores", 8, ["onClick", "disabled"]),
                _createElementVNode("button", {
                  onClick: $event => (showTaxCodeHistory(codeHistory,codeHistory.offset+100)),
                  disabled: busy||codeHistory.offset+100>=codeHistory.total
                }, "Próximas versões", 8, ["onClick", "disabled"])
              ]))
            : _createCommentVNode("", true)
        ]),
        _createElementVNode("details", { class: "catalog-import" }, [
          _createElementVNode("summary", null, "Importar cadastros com origem, versão e jurisdição"),
          _createElementVNode("p", null, "Receba CSV ou JSON no padrão documentado, até 8 MiB e 15000 registros. O recebimento preserva o arquivo sem ativar códigos. A ativação exige seleção, comparação e revisão. O formato nativo dos portais oficiais não é presumido."),
          _createElementVNode("details", null, [_createElementVNode("summary", null, "Referências oficiais e limites verificados"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(taxConfig.catalog_sources, (source) => {
            return (_openBlock(), _createElementBlock("article", {
              key: source.id,
              class: "inset"
            }, [
              _createElementVNode("b", null, _toDisplayString(source.publisher) + " · " + _toDisplayString(({cfop:'CFOP',ncm:'NCM',revenue:'Receitas',service:'Serviços'})[source.kind]), 1),
              _createElementVNode("p", null, _toDisplayString(source.limits), 1),
              _createElementVNode("a", {
                href: source.url,
                target: "_blank",
                rel: "noopener noreferrer"
              }, "Consultar referência", 8, ["href"]),
              _createElementVNode("p", null, "Verificação documental: " + _toDisplayString(source.reviewed_on) + " · " + _toDisplayString(source.status_label), 1)
            ]))
          }), 128))]),
          _createElementVNode("form", {
            onSubmit: _withModifiers(receiveCatalog, ["prevent"]),
            class: "grid"
          }, [
            _createElementVNode("label", null, [_createTextVNode("Arquivo do cadastro"), _createElementVNode("input", {
              id: "catalog-import-file",
              type: "file",
              accept: ".csv,.json",
              onChange: $event => {catalogFile=$event.target.files[0]||null;catalogReceiveAttempt=null},
              required: ""
            }, null, 40, ["onChange"])]),
            _createElementVNode("label", null, [_createTextVNode("Tipo do cadastro importado"), _withDirectives(_createElementVNode("select", {
              "aria-label": "Tipo do cadastro importado",
              "onUpdate:modelValue": $event => ((catalogMeta.kind) = $event),
              onChange: $event => {catalogMeta.system='';catalogMeta.jurisdiction=''}
            }, [
              _createElementVNode("option", { value: "cfop" }, "CFOP"),
              _createElementVNode("option", { value: "ncm" }, "NCM"),
              _createElementVNode("option", { value: "revenue" }, "Receitas"),
              _createElementVNode("option", { value: "service" }, "Serviços")
            ], 40, ["onUpdate:modelValue", "onChange"]), [[_vModelSelect, catalogMeta.kind]])]),
            _createElementVNode("label", null, [_createTextVNode("Sistema de códigos"), _withDirectives(_createElementVNode("select", {
              "aria-label": "Sistema de códigos",
              "onUpdate:modelValue": $event => ((catalogMeta.system) = $event),
              required: ""
            }, [_createElementVNode("option", { value: "" }, "Selecione"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(catalogSystems, (system) => {
              return (_openBlock(), _createElementBlock("option", null, _toDisplayString(system), 1))
            }), 256))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, catalogMeta.system]])]),
            _createElementVNode("label", null, [_createTextVNode("Jurisdição declarada"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((catalogMeta.jurisdiction) = $event),
              placeholder: "BR, UF:XX ou MUN:0000000",
              required: ""
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, catalogMeta.jurisdiction]])]),
            _createElementVNode("label", null, [_createTextVNode("Órgão ou publicador declarado"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((catalogMeta.publisher) = $event),
              required: ""
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, catalogMeta.publisher]])]),
            _createElementVNode("label", null, [_createTextVNode("URL da fonte declarada"), _withDirectives(_createElementVNode("input", {
              type: "url",
              "onUpdate:modelValue": $event => ((catalogMeta.source_url) = $event),
              placeholder: "https://",
              required: ""
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, catalogMeta.source_url]])]),
            _createElementVNode("label", null, [_createTextVNode("Edição ou versão da fonte"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((catalogMeta.edition) = $event),
              required: ""
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, catalogMeta.edition]])]),
            _createElementVNode("label", null, [_createTextVNode("Data de consulta da fonte"), _withDirectives(_createElementVNode("input", {
              type: "date",
              "onUpdate:modelValue": $event => ((catalogMeta.retrieved_on) = $event),
              required: ""
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, catalogMeta.retrieved_on]])]),
            _createElementVNode("label", null, [_createTextVNode("Recorte do arquivo"), _withDirectives(_createElementVNode("select", {
              "aria-label": "Recorte do arquivo",
              "onUpdate:modelValue": $event => ((catalogMeta.coverage) = $event)
            }, [_createElementVNode("option", { value: "parcial" }, "Parcial declarado"), _createElementVNode("option", { value: "snapshot_informado" }, "Snapshot informado, completude não certificada")], 8, ["onUpdate:modelValue"]), [[_vModelSelect, catalogMeta.coverage]])]),
            _createElementVNode("label", null, [_createTextVNode("Conversão e conferência do arquivo"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((catalogMeta.transformation_reference) = $event),
              placeholder: "Registre conversão, fonte e revisão; não há conversão automática",
              required: ""
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, catalogMeta.transformation_reference]])]),
            _createElementVNode("label", null, [_createTextVNode("Motivo da recepção do cadastro"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((catalogReceiveReason) = $event),
              required: ""
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, catalogReceiveReason]])]),
            _createElementVNode("button", { disabled: busy||!company }, "Preservar arquivo sem ativar", 8, ["disabled"])
          ], 40, ["onSubmit"]),
          _createElementVNode("p", null, "CSV UTF-8 com separador ponto e vírgula e cabeçalho code;description;valid_from;valid_to. Códigos textuais preservam zeros iniciais; datas AAAA-MM-DD são explícitas. JSON exige o perfil cadastro-fiscal-v1. URL e hash identificam a declaração e o arquivo recebido; não autenticam sua origem oficial."),
          _createElementVNode("button", {
            onClick: loadCatalogImports,
            disabled: busy||!company
          }, "Consultar arquivos recebidos", 8, ["onClick", "disabled"]),
          (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(catalogImports, (row) => {
            return (_openBlock(), _createElementBlock("article", {
              key: row.id,
              class: "inset"
            }, [_createElementVNode("b", null, "#" + _toDisplayString(row.id) + " · " + _toDisplayString(row.filename) + " · " + _toDisplayString(row.metadata.system) + " · " + _toDisplayString(row.metadata.jurisdiction), 1), _createElementVNode("p", null, _toDisplayString(row.metadata.edition) + " · " + _toDisplayString(row.total_records) + " registros · " + _toDisplayString(row.metadata.coverage==='parcial'?'recorte parcial':'snapshot informado'), 1), _createElementVNode("button", {
              onClick: $event => (openCatalogImport(row)),
              disabled: busy
            }, "Consultar importação", 8, ["onClick", "disabled"])]))
          }), 128)),
          catalogImport
            ? (_openBlock(), _createElementBlock("section", {
                key: 0,
                class: "inset"
              }, [
                _createElementVNode("h3", null, "Arquivo preservado #" + _toDisplayString(catalogImport.id), 1),
                _createElementVNode("p", null, _toDisplayString(catalogImport.metadata.publisher) + " · " + _toDisplayString(catalogImport.metadata.edition) + " · " + _toDisplayString(catalogImport.metadata.system) + " · " + _toDisplayString(catalogImport.metadata.jurisdiction), 1),
                _createElementVNode("p", { class: "tax-fingerprint" }, "SHA-256 " + _toDisplayString(catalogImport.raw_sha256), 1),
                (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(catalogImport.limits, (limit) => {
                  return (_openBlock(), _createElementBlock("p", null, _toDisplayString(limit), 1))
                }), 256)),
                _createElementVNode("button", { onClick: $event => (downloadFile('tax-catalog-original',{import_id:catalogImport.id},'cadastro-'+catalogImport.id+(catalogImport.parser.includes('json')?'.json':'.csv'))) }, "Baixar arquivo recebido", 8, ["onClick"]),
                _createElementVNode("form", {
                  class: "grid",
                  onSubmit: _withModifiers($event => (searchCatalogRecords(0)), ["prevent"])
                }, [_createElementVNode("label", null, [_createTextVNode("Buscar código ou descrição no arquivo"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((catalogQuery) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, catalogQuery]])]), _createElementVNode("button", { disabled: busy }, "Buscar no arquivo", 8, ["disabled"])], 40, ["onSubmit"]),
                _createElementVNode("p", null, _toDisplayString(catalogImport.filtered_records) + " encontrados de " + _toDisplayString(catalogImport.total_records) + " · " + _toDisplayString(catalogSelected.length) + " selecionados", 1),
                _createElementVNode("div", { class: "toolbar" }, [
                  _createElementVNode("button", {
                    onClick: selectCatalogPage,
                    disabled: busy
                  }, "Selecionar esta página", 8, ["onClick", "disabled"]),
                  _createElementVNode("button", { onClick: $event => {catalogSelected=[];catalogPreview=null} }, "Limpar seleção", 8, ["onClick"]),
                  _createElementVNode("button", {
                    onClick: $event => (searchCatalogRecords(Math.max(0,catalogImport.offset-100))),
                    disabled: busy||catalogImport.offset===0
                  }, "Página anterior", 8, ["onClick", "disabled"]),
                  _createElementVNode("button", {
                    onClick: $event => (searchCatalogRecords(catalogImport.offset+100)),
                    disabled: busy||catalogImport.offset+100>=catalogImport.filtered_records
                  }, "Próxima página", 8, ["onClick", "disabled"])
                ]),
                _createElementVNode("div", { class: "table-scroll" }, [_createElementVNode("table", null, [_createElementVNode("thead", null, [_createElementVNode("tr", null, [
                  _createElementVNode("th", null, "Selecionar"),
                  _createElementVNode("th", null, "Código"),
                  _createElementVNode("th", null, "Descrição"),
                  _createElementVNode("th", null, "Vigência na fonte")
                ])]), _createElementVNode("tbody", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(catalogImport.records, (row) => {
                  return (_openBlock(), _createElementBlock("tr", { key: row.code }, [
                    _createElementVNode("td", null, [_withDirectives(_createElementVNode("input", {
                      type: "checkbox",
                      "aria-label": 'Selecionar código '+row.code,
                      value: row.code,
                      "onUpdate:modelValue": $event => ((catalogSelected) = $event),
                      onChange: $event => (catalogPreview=null)
                    }, null, 40, ["aria-label", "value", "onUpdate:modelValue", "onChange"]), [[_vModelCheckbox, catalogSelected]])]),
                    _createElementVNode("td", null, _toDisplayString(row.code), 1),
                    _createElementVNode("td", null, _toDisplayString(row.description), 1),
                    _createElementVNode("td", null, _toDisplayString(row.valid_from) + " a " + _toDisplayString(row.valid_to||'fim não informado'), 1)
                  ]))
                }), 128))])])]),
                _createElementVNode("label", null, [_createTextVNode("Aplicar a partir de"), _withDirectives(_createElementVNode("input", {
                  type: "date",
                  "onUpdate:modelValue": $event => ((catalogFrom) = $event),
                  onChange: $event => (catalogPreview=null)
                }, null, 40, ["onUpdate:modelValue", "onChange"]), [[_vModelText, catalogFrom]])]),
                _createElementVNode("button", {
                  onClick: previewCatalog,
                  disabled: busy||!catalogSelected.length
                }, "Conferir prévia dos códigos selecionados", 8, ["onClick", "disabled"]),
                catalogPreview
                  ? (_openBlock(), _createElementBlock("div", { key: 0 }, [
                      (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(catalogPreview.snapshot.blockers, (blocker) => {
                        return (_openBlock(), _createElementBlock("p", { class: "error" }, _toDisplayString(blocker), 1))
                      }), 256)),
                      _createElementVNode("p", null, "O início local será o maior entre a data declarada de aplicação e o início registrado no arquivo. A vigência original permanece na origem da versão. Códigos ausentes não serão inativados."),
                      _createVNode(_component_data_table, {
                        rows: catalogPreview.snapshot.changes.map(c=>({code:c.code,previous_version:c.expected_version,previous_state:c.previous?.state||'novo',proposed_state:c.state,previous_description:c.previous?.data.description||'',description:c.data.description,valid_from:c.data.valid_from,valid_to:c.data.valid_to})),
                        columns: {code:'Código',previous_version:'Versão anterior',previous_state:'Estado anterior',proposed_state:'Estado proposto',previous_description:'Descrição anterior',description:'Descrição proposta',valid_from:'Início local',valid_to:'Fim informado'}
                      }, null, 8, ["rows", "columns"]),
                      _createElementVNode("label", null, [_createTextVNode("Referência da revisão do cadastro"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((catalogReviewReference) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, catalogReviewReference]])]),
                      _createElementVNode("label", null, [_createTextVNode("Motivo da aplicação do cadastro"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((catalogApplyReason) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, catalogApplyReason]])]),
                      _createElementVNode("label", null, [_withDirectives(_createElementVNode("input", {
                        type: "checkbox",
                        "onUpdate:modelValue": $event => ((catalogConfirmed) = $event)
                      }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, catalogConfirmed]]), _createTextVNode(" Conferi conteúdo, origem declarada, vigências, códigos selecionados e jurisdição")]),
                      (catalogPreview.snapshot.legacy_count)
                        ? (_openBlock(), _createElementBlock("label", { key: 0 }, [_withDirectives(_createElementVNode("input", {
                            type: "checkbox",
                            "onUpdate:modelValue": $event => ((catalogLegacyAcknowledged) = $event)
                          }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, catalogLegacyAcknowledged]]), _createTextVNode(" Conferi os códigos legados selecionados sem escopo vinculado; o vínculo novo não certifica esses registros anteriores")]))
                        : _createCommentVNode("", true),
                      _createElementVNode("button", {
                        onClick: applyCatalog,
                        disabled: busy||!catalogConfirmed||catalogPreview.snapshot.blockers.length
                      }, "Ativar códigos conferidos nesta empresa", 8, ["onClick", "disabled"])
                    ]))
                  : _createCommentVNode("", true),
                (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(catalogApplications, (row) => {
                  return (_openBlock(), _createElementBlock("article", {
                    key: row.id,
                    class: "inset"
                  }, [_createElementVNode("b", null, "Aplicação #" + _toDisplayString(row.id) + " · " + _toDisplayString(row.version_count) + " versões · " + _toDisplayString(row.created_at), 1), _createElementVNode("p", null, _toDisplayString(row.review_reference), 1), _createElementVNode("button", { onClick: $event => (downloadCatalogManifest(row)) }, "Baixar manifesto da aplicação", 8, ["onClick"])]))
                }), 128))
              ]))
            : _createCommentVNode("", true)
        ]),
        _createElementVNode("details", { open: "" }, [
          _createElementVNode("summary", null, "Regras por empresa"),
          _createElementVNode("div", { class: "toolbar" }, [_createElementVNode("button", { onClick: newTaxRule }, "Nova regra", 8, ["onClick"]), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(taxConfig.structural_models, (model) => {
            return (_openBlock(), _createElementBlock("button", { onClick: $event => (useTaxModel(model)) }, _toDisplayString(model.label), 9, ["onClick"]))
          }), 256))]),
          _createElementVNode("form", {
            onSubmit: _withModifiers($event => (saveTaxRule('rascunho')), ["prevent"]),
            class: "grid"
          }, [
            _createElementVNode("label", null, [_createTextVNode("Identificador da regra"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((taxForm.rule_key) = $event),
              disabled: taxForm.expected_version>0,
              required: "",
              maxlength: "80"
            }, null, 8, ["onUpdate:modelValue", "disabled"]), [[_vModelText, taxForm.rule_key]])]),
            _createElementVNode("label", null, [_createTextVNode("Nome da regra"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((taxForm.label) = $event),
              required: "",
              maxlength: "200"
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, taxForm.label]])]),
            _createElementVNode("label", null, [_createTextVNode("Tributo da regra"), _withDirectives(_createElementVNode("select", {
              "aria-label": "Tributo da regra",
              "onUpdate:modelValue": $event => ((taxForm.spec.tax) = $event)
            }, [
              _createElementVNode("option", { value: "" }, "Selecione"),
              _createElementVNode("option", null, "ICMS"),
              _createElementVNode("option", null, "ISS"),
              _createElementVNode("option", null, "PIS"),
              _createElementVNode("option", null, "COFINS"),
              _createElementVNode("option", null, "ICMS_ST"),
              _createElementVNode("option", null, "ICMS_DIFAL"),
              _createElementVNode("option", null, "RETENCAO"),
              _createElementVNode("option", null, "FCP")
            ], 8, ["onUpdate:modelValue"]), [[_vModelSelect, taxForm.spec.tax]])]),
            _createElementVNode("label", null, [_createTextVNode("Natureza da regra"), _withDirectives(_createElementVNode("select", {
              "aria-label": "Natureza da regra",
              "onUpdate:modelValue": $event => ((taxForm.spec.operation) = $event)
            }, [
              _createElementVNode("option", { value: "" }, "Selecione"),
              _createElementVNode("option", { value: "entrada" }, "Entrada"),
              _createElementVNode("option", { value: "saida" }, "Saída"),
              _createElementVNode("option", { value: "servico_tomado" }, "Serviço tomado"),
              _createElementVNode("option", { value: "servico_prestado" }, "Serviço prestado"),
              _createElementVNode("option", { value: "ajuste" }, "Ajuste informado")
            ], 8, ["onUpdate:modelValue"]), [[_vModelSelect, taxForm.spec.operation]])]),
            _createElementVNode("label", null, [_createTextVNode("Modelo da regra"), _withDirectives(_createElementVNode("select", {
              "aria-label": "Modelo da regra",
              "onUpdate:modelValue": $event => ((taxForm.spec.model) = $event)
            }, [
              _createElementVNode("option", { value: "" }, "Todos os modelos"),
              _createElementVNode("option", null, "55"),
              _createElementVNode("option", null, "65"),
              _createElementVNode("option", null, "SERVICO")
            ], 8, ["onUpdate:modelValue"]), [[_vModelSelect, taxForm.spec.model]])]),
            _createElementVNode("label", null, [_createTextVNode("CFOP de escopo"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((taxForm.spec.cfop) = $event),
              maxlength: "4"
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, taxForm.spec.cfop]])]),
            _createElementVNode("label", null, [_createTextVNode("NCM de escopo"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((taxForm.spec.ncm) = $event),
              maxlength: "8"
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, taxForm.spec.ncm]])]),
            _createElementVNode("label", null, [_createTextVNode("Código de serviço de escopo"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((taxForm.spec.service_code) = $event),
              maxlength: "30"
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, taxForm.spec.service_code]])]),
            _createElementVNode("label", null, [_createTextVNode("Código de receita da regra"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((taxForm.spec.revenue_code) = $event),
              maxlength: "30"
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, taxForm.spec.revenue_code]])]),
            _createElementVNode("label", null, [_createTextVNode("Campo da base"), _withDirectives(_createElementVNode("select", {
              "aria-label": "Campo da base",
              "onUpdate:modelValue": $event => ((taxForm.spec.base_field) = $event),
              disabled: taxGrossupActive
            }, [
              _createElementVNode("option", { value: "" }, "Selecione explicitamente"),
              _createElementVNode("option", { value: "total" }, "Total declarado do documento"),
              _createElementVNode("option", { value: "icms_base" }, "Base ICMS declarada"),
              _createElementVNode("option", { value: "iss_base" }, "Base ISS declarada"),
              _createElementVNode("option", { value: "pis_base" }, "Base PIS declarada"),
              _createElementVNode("option", { value: "cofins_base" }, "Base COFINS declarada"),
              (taxForm.spec.calculation)
                ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [
                    _createElementVNode("option", { value: "st_base" }, "Base ST declarada do item"),
                    _createElementVNode("option", { value: "difal_base" }, "Base DIFAL declarada do item"),
                    _createElementVNode("option", { value: "retention_base" }, "Base de retenção declarada do item"),
                    _createElementVNode("option", { value: "fcp_base" }, "Base FCP declarada do item"),
                    _createElementVNode("option", { value: "net_base" }, "Base líquida sem componentes do grupo por dentro")
                  ], 64))
                : _createCommentVNode("", true)
            ], 8, ["onUpdate:modelValue", "disabled"]), [[_vModelSelect, taxForm.spec.base_field]])]),
            _createElementVNode("label", null, [_createTextVNode("Perfil de cálculo"), _createElementVNode("select", {
              "aria-label": "Perfil de cálculo",
              value: taxForm.spec.calculation?.method||'documento',
              onChange: $event => (setTaxCalculation($event.target.value))
            }, [
              _createElementVNode("option", { value: "documento" }, "Percentual documental"),
              _createElementVNode("option", { value: "percentual" }, "Percentual por item"),
              _createElementVNode("option", { value: "retencao" }, "Retenção declarada por item"),
              _createElementVNode("option", { value: "st" }, "ST declarada por item, com margem e dedução"),
              _createElementVNode("option", { value: "difal" }, "Diferença de taxas declaradas por item"),
              _createElementVNode("option", { value: "fcp" }, "FCP por item e modalidade declarada"),
              _createElementVNode("option", { value: "por_dentro" }, "Por dentro com base líquida e grupo declarado")
            ], 40, ["value", "onChange"])]),
            (taxForm.spec.calculation)
              ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [
                  _createElementVNode("label", null, [_createTextVNode("Tratamento de escopo do item"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((taxForm.spec.item_treatment) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, taxForm.spec.item_treatment]])]),
                  _createElementVNode("label", null, [_createTextVNode("Redução percentual declarada"), _withDirectives(_createElementVNode("input", {
                    "onUpdate:modelValue": $event => ((taxForm.spec.calculation.reduction_percent) = $event),
                    inputmode: "decimal",
                    placeholder: "Informe inclusive zero"
                  }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, taxForm.spec.calculation.reduction_percent]])]),
                  _createElementVNode("label", null, [_createTextVNode("Arredondamento da base do item"), _withDirectives(_createElementVNode("select", {
                    "aria-label": "Arredondamento da base do item",
                    "onUpdate:modelValue": $event => ((taxForm.spec.calculation.base_rounding) = $event)
                  }, [_createElementVNode("option", { value: "" }, "Selecione explicitamente"), _createElementVNode("option", { value: "centavos_antes_da_taxa" }, "Centavos antes da taxa, conforme arredondamento da regra")], 8, ["onUpdate:modelValue"]), [[_vModelSelect, taxForm.spec.calculation.base_rounding]])]),
                  (taxForm.spec.calculation.method==='st')
                    ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [_createElementVNode("label", null, [_createTextVNode("Margem percentual declarada"), _withDirectives(_createElementVNode("input", {
                        "onUpdate:modelValue": $event => ((taxForm.spec.calculation.margin_percent) = $event),
                        inputmode: "decimal"
                      }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, taxForm.spec.calculation.margin_percent]])]), _createElementVNode("p", null, "A dedução própria deve ser informada em cada item, inclusive zero. O perfil não calcula a dedução.")], 64))
                    : _createCommentVNode("", true),
                  (taxForm.spec.calculation.method==='difal')
                    ? (_openBlock(), _createElementBlock("label", { key: 1 }, [_createTextVNode("Taxa de origem declarada"), _withDirectives(_createElementVNode("input", {
                        "onUpdate:modelValue": $event => ((taxForm.spec.calculation.origin_rate) = $event),
                        inputmode: "decimal"
                      }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, taxForm.spec.calculation.origin_rate]])]))
                    : _createCommentVNode("", true),
                  (['st','difal'].includes(taxForm.spec.calculation.method))
                    ? (_openBlock(), _createElementBlock("label", { key: 2 }, [_createTextVNode("Tratamento de resultado negativo"), _withDirectives(_createElementVNode("select", {
                        "aria-label": "Tratamento de resultado negativo",
                        "onUpdate:modelValue": $event => ((taxForm.spec.calculation.negative_policy) = $event)
                      }, [_createElementVNode("option", { value: "" }, "Selecione explicitamente"), _createElementVNode("option", { value: "bloquear" }, "Bloquear para revisão"), _createElementVNode("option", { value: "zerar" }, "Zerar por parâmetro validado, preservando resultado original")], 8, ["onUpdate:modelValue"]), [[_vModelSelect, taxForm.spec.calculation.negative_policy]])]))
                    : _createCommentVNode("", true),
                  (taxForm.spec.calculation.method==='retencao')
                    ? (_openBlock(), _createElementBlock("label", { key: 3 }, [_createTextVNode("Identificador do tributo retido"), _withDirectives(_createElementVNode("input", {
                        "onUpdate:modelValue": $event => ((taxForm.spec.calculation.component_code) = $event),
                        placeholder: "Código declarado pelo responsável"
                      }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, taxForm.spec.calculation.component_code]])]))
                    : _createCommentVNode("", true),
                  (taxForm.spec.calculation.method==='fcp')
                    ? (_openBlock(), _createElementBlock(_Fragment, { key: 4 }, [_createElementVNode("label", null, [_createTextVNode("Identificador da modalidade FCP"), _withDirectives(_createElementVNode("input", {
                        "onUpdate:modelValue": $event => ((taxForm.spec.calculation.component_code) = $event),
                        placeholder: "Modalidade declarada, sem classificação automática"
                      }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, taxForm.spec.calculation.component_code]])]), _createElementVNode("label", null, [_createTextVNode("Formação da base FCP"), _createElementVNode("select", {
                        "aria-label": "Formação da base FCP",
                        value: taxForm.spec.calculation.base_mode,
                        onChange: $event => (setFCPBaseMode($event.target.value))
                      }, [_createElementVNode("option", { value: "" }, "Selecione explicitamente"), _createElementVNode("option", { value: "declarada" }, "Base informada do item"), _createElementVNode("option", { value: "por_dentro" }, "Base recomposta por grupo declarado")], 40, ["value", "onChange"])])], 64))
                    : _createCommentVNode("", true),
                  taxGrossupActive
                    ? (_openBlock(), _createElementBlock(_Fragment, { key: 5 }, [
                        _createElementVNode("label", null, [_createTextVNode("Significado da base líquida"), _withDirectives(_createElementVNode("select", {
                          "aria-label": "Significado da base líquida",
                          "onUpdate:modelValue": $event => ((taxForm.spec.calculation.input_basis) = $event)
                        }, [_createElementVNode("option", { value: "" }, "Confirme explicitamente"), _createElementVNode("option", { value: "liquido_sem_componentes_do_grupo" }, "Líquida sem os componentes declarados do grupo")], 8, ["onUpdate:modelValue"]), [[_vModelSelect, taxForm.spec.calculation.input_basis]])]),
                        _createElementVNode("label", null, [_createTextVNode("Diferença de arredondamento do grupo"), _withDirectives(_createElementVNode("select", {
                          "aria-label": "Diferença de arredondamento do grupo",
                          "onUpdate:modelValue": $event => ((taxForm.spec.calculation.residual_policy) = $event)
                        }, [_createElementVNode("option", { value: "" }, "Selecione explicitamente"), _createElementVNode("option", { value: "bloquear" }, "Bloquear para revisão"), _createElementVNode("option", { value: "preservar_sem_rateio" }, "Preservar diferença, sem rateio automático")], 8, ["onUpdate:modelValue"]), [[_vModelSelect, taxForm.spec.calculation.residual_policy]])]),
                        _createElementVNode("fieldset", { class: "inset" }, [
                          _createElementVNode("legend", null, "Componentes declarados no denominador"),
                          _createElementVNode("p", null, "Declare todas as taxas, inclusive a do componente calculado. O grupo exige regras compatíveis para cada componente; FCP não é incluído automaticamente."),
                          (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(taxForm.spec.calculation.denominator_components, (component, index) => {
                            return (_openBlock(), _createElementBlock("div", {
                              class: "grid",
                              key: index,
                              "data-grossup-component": index
                            }, [_createElementVNode("label", null, [_createTextVNode("Componente incluído por dentro"), _withDirectives(_createElementVNode("input", {
                              "onUpdate:modelValue": $event => ((component.component) = $event),
                              placeholder: "ICMS ou FCP:IDENTIFICADOR"
                            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, component.component]])]), _createElementVNode("label", null, [_createTextVNode("Taxa incluída no denominador (%)"), _withDirectives(_createElementVNode("input", {
                              "onUpdate:modelValue": $event => ((component.rate) = $event),
                              inputmode: "decimal"
                            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, component.rate]])]), _createElementVNode("button", {
                              type: "button",
                              onClick: $event => (taxForm.spec.calculation.denominator_components.splice(index,1))
                            }, "Remover componente do denominador", 8, ["onClick"])], 8, ["data-grossup-component"]))
                          }), 128)),
                          _createElementVNode("button", {
                            type: "button",
                            onClick: addGrossupComponent
                          }, "Adicionar componente ao denominador", 8, ["onClick"])
                        ]),
                        _createElementVNode("p", null, "Base bruta = base líquida reduzida ÷ (1 − soma das taxas declaradas ÷ 100). A soma deve ser menor que 100%. Todos os membros precisam declarar o mesmo grupo, base, redução e arredondamento. Não há inferência de incidência ou rateio de diferenças.")
                      ], 64))
                    : _createCommentVNode("", true),
                  _createElementVNode("p", null, "Perfil aritmético limitado: base reduzida arredondada antes da taxa; valores por item arredondados antes da soma. Não infere incidência, bases legais, partilha ou efeito financeiro. FCP e cálculo por dentro exigem os perfis próprios e parâmetros explícitos. No perfil de diferença, a alíquota principal representa a taxa de destino.")
                ], 64))
              : _createCommentVNode("", true),
            _createElementVNode("label", null, [_createTextVNode("Alíquota percentual informada"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((taxForm.spec.rate) = $event),
              inputmode: "decimal",
              placeholder: "Sem alíquota presumida"
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, taxForm.spec.rate]])]),
            _createElementVNode("label", null, [_createTextVNode("Efeito na apuração"), _withDirectives(_createElementVNode("select", {
              "aria-label": "Efeito na apuração",
              "onUpdate:modelValue": $event => ((taxForm.spec.effect) = $event)
            }, [
              _createElementVNode("option", { value: "" }, "Selecione explicitamente"),
              _createElementVNode("option", { value: "debito" }, "Débito declarado"),
              _createElementVNode("option", { value: "credito" }, "Crédito declarado"),
              _createElementVNode("option", { value: "informativo" }, "Informativo")
            ], 8, ["onUpdate:modelValue"]), [[_vModelSelect, taxForm.spec.effect]])]),
            _createElementVNode("label", null, [_createTextVNode("Arredondamento da regra"), _withDirectives(_createElementVNode("select", {
              "aria-label": "Arredondamento da regra",
              "onUpdate:modelValue": $event => ((taxForm.spec.rounding) = $event)
            }, [_createElementVNode("option", { value: "" }, "Selecione explicitamente"), _createElementVNode("option", { value: "meio_para_cima" }, "Meio para cima, centavos"), _createElementVNode("option", { value: "truncar" }, "Truncar em centavos")], 8, ["onUpdate:modelValue"]), [[_vModelSelect, taxForm.spec.rounding]])]),
            _createElementVNode("label", null, [_createTextVNode("Início da vigência da regra"), _withDirectives(_createElementVNode("input", {
              type: "date",
              "onUpdate:modelValue": $event => ((taxForm.spec.valid_from) = $event)
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, taxForm.spec.valid_from]])]),
            _createElementVNode("label", null, [_createTextVNode("Fim da vigência da regra"), _withDirectives(_createElementVNode("input", {
              type: "date",
              "onUpdate:modelValue": $event => ((taxForm.spec.valid_to) = $event)
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, taxForm.spec.valid_to]])]),
            _createElementVNode("label", null, [_createTextVNode("Referência da validação da regra"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((taxForm.spec.validation_reference) = $event),
              maxlength: "1000"
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, taxForm.spec.validation_reference]])]),
            _createElementVNode("label", null, [_createTextVNode("Motivo da versão da regra"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((taxForm.reason) = $event),
              required: ""
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, taxForm.reason]])]),
            _createElementVNode("button", { disabled: busy||!company }, "Salvar regra como rascunho", 8, ["disabled"]),
            _createElementVNode("button", {
              type: "button",
              onClick: $event => (saveTaxRule('aprovada')),
              disabled: busy||!company
            }, "Aprovar versão da regra", 8, ["onClick", "disabled"]),
            _createElementVNode("button", {
              type: "button",
              onClick: $event => (saveTaxRule('inativa')),
              disabled: busy||!taxForm.expected_version
            }, "Inativar por nova versão", 8, ["onClick", "disabled"])
          ], 40, ["onSubmit"]),
          (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(latestTaxRules, (rule) => {
            return (_openBlock(), _createElementBlock("article", {
              key: rule.id,
              class: "inset"
            }, [
              _createElementVNode("b", null, _toDisplayString(rule.label) + " · " + _toDisplayString(rule.spec.tax||'tributo a definir') + " · " + _toDisplayString(rule.state) + " · v" + _toDisplayString(rule.version), 1),
              _createElementVNode("p", null, _toDisplayString(rule.spec.operation) + " · base " + _toDisplayString(rule.spec.base_field) + " · taxa " + _toDisplayString(rule.spec.rate||'não informada') + "% · " + _toDisplayString(rule.spec.effect), 1),
              (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(rule.issues, (issue) => {
                return (_openBlock(), _createElementBlock("p", null, _toDisplayString(issue), 1))
              }), 256)),
              _createElementVNode("button", { onClick: $event => (editTaxRule(rule)) }, "Editar regra", 8, ["onClick"])
            ]))
          }), 128)),
          _createElementVNode("details", null, [_createElementVNode("summary", null, "Histórico de regras e parâmetros"), _createVNode(_component_data_table, {
            rows: taxConfig.rules,
            columns: {rule_key:'Regra',version:'Versão',state:'Estado',spec:'Parâmetros',source:'Origem do modelo',actor:'Responsável',reason:'Motivo'}
          }, null, 8, ["rows", "columns"])])
        ]),
        _createElementVNode("details", null, [
          _createElementVNode("summary", null, "Modelos reutilizáveis e cópia independente"),
          _createElementVNode("p", null, "Os modelos estruturais não contêm alíquotas. Um modelo salvo preserva uma versão aprovada; sua cópia sempre nasce em rascunho e precisa de validação na empresa de destino. Tabelas de códigos devem estar cadastradas e vigentes no destino."),
          _createElementVNode("form", {
            onSubmit: _withModifiers(saveTaxTemplate, ["prevent"]),
            class: "grid"
          }, [
            _createElementVNode("label", null, [_createTextVNode("Regra aprovada para modelo"), _withDirectives(_createElementVNode("select", {
              "aria-label": "Regra aprovada para modelo",
              "onUpdate:modelValue": $event => ((templateForm.rule_id) = $event)
            }, [_createElementVNode("option", { value: "" }, "Selecione"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(taxConfig.rules.filter(r=>r.state==='aprovada'), (r) => {
              return (_openBlock(), _createElementBlock("option", { value: String(r.id) }, _toDisplayString(r.label) + " · v" + _toDisplayString(r.version), 9, ["value"]))
            }), 256))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, templateForm.rule_id]])]),
            _createElementVNode("label", null, [_createTextVNode("Nome do modelo"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((templateForm.label) = $event),
              required: ""
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, templateForm.label]])]),
            _createElementVNode("label", null, [_createTextVNode("Motivo do modelo"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((templateForm.reason) = $event),
              required: ""
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, templateForm.reason]])]),
            _createElementVNode("button", { disabled: busy }, "Preservar modelo da regra", 8, ["disabled"])
          ], 40, ["onSubmit"]),
          _createElementVNode("form", {
            onSubmit: _withModifiers(copyTaxTemplate, ["prevent"]),
            class: "grid"
          }, [
            _createElementVNode("label", null, [_createTextVNode("Empresa de origem do modelo"), _withDirectives(_createElementVNode("select", {
              "aria-label": "Empresa de origem do modelo",
              "onUpdate:modelValue": $event => ((templateSource) = $event),
              onChange: loadTemplateSource
            }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(companies, (c) => {
              return (_openBlock(), _createElementBlock("option", { value: String(c.id) }, _toDisplayString(c.name), 9, ["value"]))
            }), 256))], 40, ["onUpdate:modelValue", "onChange"]), [[_vModelSelect, templateSource]])]),
            _createElementVNode("label", null, [_createTextVNode("Modelo a copiar"), _withDirectives(_createElementVNode("select", {
              "aria-label": "Modelo a copiar",
              "onUpdate:modelValue": $event => ((copyForm.template_id) = $event)
            }, [_createElementVNode("option", { value: "" }, "Selecione"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(copyTemplates, (t) => {
              return (_openBlock(), _createElementBlock("option", { value: String(t.id) }, _toDisplayString(t.label) + " · v" + _toDisplayString(t.version), 9, ["value"]))
            }), 256))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, copyForm.template_id]])]),
            _createElementVNode("label", null, [_createTextVNode("Identificador da regra copiada"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((copyForm.rule_key) = $event),
              required: ""
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, copyForm.rule_key]])]),
            _createElementVNode("label", null, [_createTextVNode("Nome da regra copiada"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((copyForm.label) = $event),
              required: ""
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, copyForm.label]])]),
            _createElementVNode("label", null, [_createTextVNode("Motivo da cópia"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((copyForm.reason) = $event),
              required: ""
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, copyForm.reason]])]),
            _createElementVNode("button", { disabled: busy }, "Copiar modelo como rascunho", 8, ["disabled"])
          ], 40, ["onSubmit"])
        ]),
        _createElementVNode("details", { class: "inset" }, [
          _createElementVNode("summary", null, "Tributação em lote com prévia e conferência"),
          _createElementVNode("p", null, "Selecione até 100 operações salvas desta competência. A aplicação só ocorre quando todas puderem ser calculadas pelas regras aprovadas. O lote cria rascunhos; conferência e escrituração continuam por operação."),
          _createElementVNode("label", null, [_createTextVNode("Buscar operação para o lote"), _withDirectives(_createElementVNode("input", {
            "onUpdate:modelValue": $event => ((taxBatchQuery) = $event),
            disabled: busy,
            placeholder: "Número interno ou referência"
          }, null, 8, ["onUpdate:modelValue", "disabled"]), [[_vModelText, taxBatchQuery]])]),
          _createElementVNode("label", null, [_withDirectives(_createElementVNode("input", {
            type: "checkbox",
            "onUpdate:modelValue": $event => ((taxBatchOnlyPending) = $event),
            disabled: busy
          }, null, 8, ["onUpdate:modelValue", "disabled"]), [[_vModelCheckbox, taxBatchOnlyPending]]), _createTextVNode(" Exibir somente operações sem memória")]),
          _createElementVNode("p", null, "Até 100 fichas visíveis; refine a busca. Selecionadas: " + _toDisplayString(taxBatchSelected.length) + ". A prévia considera também seleções fora do filtro atual.", 1),
          _createElementVNode("div", { class: "toolbar" }, [_createElementVNode("button", {
            type: "button",
            onClick: selectTaxBatchVisible,
            disabled: busy||!taxBatchCandidates.length
          }, "Selecionar visíveis sem memória", 8, ["onClick", "disabled"]), _createElementVNode("button", {
            type: "button",
            onClick: clearTaxBatchSelection,
            disabled: busy||!taxBatchSelected.length
          }, "Limpar seleção do lote", 8, ["onClick", "disabled"])]),
          _createElementVNode("div", { class: "table-scroll" }, [_createElementVNode("table", null, [_createElementVNode("thead", null, [_createElementVNode("tr", null, [
            _createElementVNode("th", null, "Selecionar"),
            _createElementVNode("th", null, "Operação"),
            _createElementVNode("th", null, "Referência"),
            _createElementVNode("th", null, "Estado"),
            _createElementVNode("th", null, "Memória atual")
          ])]), _createElementVNode("tbody", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(taxBatchCandidates, (row) => {
            return (_openBlock(), _createElementBlock("tr", { key: row.operation_id }, [
              _createElementVNode("td", null, [_createElementVNode("label", null, [_withDirectives(_createElementVNode("input", {
                type: "checkbox",
                "aria-label": 'Selecionar operação '+row.operation_id+' para tributação',
                disabled: busy,
                value: row.operation_id,
                "onUpdate:modelValue": $event => ((taxBatchSelected) = $event),
                onChange: $event => {taxBatchPreview=null;taxBatchConfirmed=false;taxBatchInspect=null}
              }, null, 40, ["aria-label", "disabled", "value", "onUpdate:modelValue", "onChange"]), [[_vModelCheckbox, taxBatchSelected]]), _createTextVNode(" Incluir")])]),
              _createElementVNode("td", null, _toDisplayString(row.operation_id), 1),
              _createElementVNode("td", null, _toDisplayString(row.payload.reference), 1),
              _createElementVNode("td", null, _toDisplayString(row.state), 1),
              _createElementVNode("td", null, _toDisplayString(row.payload.tax_calculation?.id||'sem memória'), 1)
            ]))
          }), 128))])])]),
          _createElementVNode("button", {
            type: "button",
            onClick: previewTaxBatch,
            disabled: busy||!taxBatchSelected.length||taxBatchSelected.length>100
          }, "Gerar prévia tributária do lote", 8, ["onClick", "disabled"]),
          taxBatchPreview
            ? (_openBlock(), _createElementBlock("div", {
                key: 0,
                class: "inset"
              }, [
                _createElementVNode("h3", null, "Prévia da tributação em lote"),
                _createElementVNode("p", null, _toDisplayString(taxBatchPreview.snapshot.ready?'Todas as operações calculáveis; confira a memória de cada ficha.':'Existem pendências; nenhuma operação pode ser aplicada neste lote.'), 1),
                (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(taxBatchPreview.snapshot.items, (row) => {
                  return (_openBlock(), _createElementBlock("article", {
                    key: row.operation_id,
                    "data-tax-batch-preview": row.operation_id
                  }, [_createElementVNode("b", null, "#" + _toDisplayString(row.operation_id) + " · " + _toDisplayString(row.reference||'operação indisponível') + " · v" + _toDisplayString(row.input_version||'—'), 1), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(row.blockers, (blocker) => {
                    return (_openBlock(), _createElementBlock("p", { class: "error" }, _toDisplayString(blocker), 1))
                  }), 256)), (row.memory)
                    ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [_createElementVNode("p", null, _toDisplayString(row.memory.profile) + " · " + _toDisplayString(row.memory.lines.length) + " linhas de cálculo. Totais por componente somam itens; efeitos mistos devem ser conferidos na memória, sem deduzir saldo líquido.", 1), _createVNode(_component_data_table, {
                        rows: row.components,
                        columns: {tax:'Tributo',component_key:'Componente',base:'Base proposta',rate:'Taxa (%)',amount:'Valor calculado',effect:'Efeito declarado'}
                      }, null, 8, ["rows", "columns"]), _createElementVNode("button", {
                        type: "button",
                        onClick: $event => (taxBatchInspect=row)
                      }, "Inspecionar memória da operação " + _toDisplayString(row.operation_id), 9, ["onClick"])], 64))
                    : _createCommentVNode("", true)], 8, ["data-tax-batch-preview"]))
                }), 128)),
                taxBatchInspect
                  ? (_openBlock(), _createElementBlock("div", { key: 0 }, [_createElementVNode("h4", null, "Memória da operação " + _toDisplayString(taxBatchInspect.operation_id), 1), _createElementVNode("pre", null, _toDisplayString(JSON.stringify(taxBatchInspect.memory,null,2)), 1)]))
                  : _createCommentVNode("", true),
                _createElementVNode("label", null, [_createTextVNode("Motivo da tributação em lote"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((taxBatchReason) = $event),
                  disabled: busy,
                  required: ""
                }, null, 8, ["onUpdate:modelValue", "disabled"]), [[_vModelText, taxBatchReason]])]),
                _createElementVNode("label", null, [_withDirectives(_createElementVNode("input", {
                  type: "checkbox",
                  "onUpdate:modelValue": $event => ((taxBatchConfirmed) = $event),
                  disabled: busy
                }, null, 8, ["onUpdate:modelValue", "disabled"]), [[_vModelCheckbox, taxBatchConfirmed]]), _createTextVNode(" Conferi todas as operações selecionadas, regras, bases, taxas, efeitos e valores da prévia do lote")]),
                _createElementVNode("button", {
                  type: "button",
                  onClick: applyTaxBatch,
                  disabled: busy||!taxBatchPreview.snapshot.ready||!taxBatchConfirmed
                }, "Aplicar lote em novas versões de rascunho", 8, ["onClick", "disabled"])
              ]))
            : _createCommentVNode("", true),
          _createElementVNode("div", { class: "toolbar" }, [_createElementVNode("button", {
            type: "button",
            onClick: $event => (loadTaxBatches(0)),
            disabled: busy||!cycle
          }, "Consultar histórico de lotes tributários", 8, ["onClick", "disabled"]), _createElementVNode("button", {
            type: "button",
            onClick: $event => (loadTaxBatches(Math.max(0,taxBatchHistory.offset-taxBatchHistory.limit))),
            disabled: busy||!taxBatchHistory.offset
          }, "Lotes anteriores na lista", 8, ["onClick", "disabled"]), _createElementVNode("button", {
            type: "button",
            onClick: $event => (loadTaxBatches(taxBatchHistory.offset+taxBatchHistory.limit)),
            disabled: busy||taxBatchHistory.offset+taxBatchHistory.limit>=taxBatchHistory.total
          }, "Próxima página de lotes", 8, ["onClick", "disabled"])]),
          _createElementVNode("p", null, _toDisplayString(taxBatchHistory.total) + " lotes preservados nesta competência", 1),
          (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(taxBatchHistory.items, (row) => {
            return (_openBlock(), _createElementBlock("article", {
              class: "inset",
              key: row.id
            }, [_createElementVNode("b", null, "Lote #" + _toDisplayString(row.id) + " · " + _toDisplayString(row.count) + " operações", 1), _createElementVNode("p", null, _toDisplayString(row.reason) + " · " + _toDisplayString(row.actor) + " · " + _toDisplayString(row.created_at), 1), _createElementVNode("button", {
              type: "button",
              onClick: $event => (openTaxBatch(row))
            }, "Abrir manifesto do lote " + _toDisplayString(row.id), 9, ["onClick"])]))
          }), 128)),
          taxBatchReceipt
            ? (_openBlock(), _createElementBlock("article", {
                key: 1,
                class: "inset"
              }, [
                _createElementVNode("h3", null, "Manifesto do lote #" + _toDisplayString(taxBatchReceipt.id), 1),
                _createElementVNode("p", null, "Preserva as versões produzidas; operações podem ter sido alteradas ou escrituradas posteriormente."),
                _createVNode(_component_data_table, {
                  rows: taxBatchReceipt.snapshot.items,
                  columns: {operation_id:'Operação',reference:'Referência',input_version:'Versão de entrada',output_version:'Versão produzida',calculation_id:'Cálculo',memory_hash:'Hash da memória'}
                }, null, 8, ["rows", "columns"]),
                _createElementVNode("button", {
                  type: "button",
                  onClick: downloadTaxBatch
                }, "Baixar manifesto e memórias do lote", 8, ["onClick"])
              ]))
            : _createCommentVNode("", true)
        ]),
        _createElementVNode("details", { class: "inset" }, [
          _createElementVNode("summary", null, "Ajustes de apuração e saldos entre competências"),
          _createElementVNode("p", null, "Ajustes exigem referência e conferência explícitas. Transporte preserva componente, receita e natureza do saldo de uma apuração validada com fiscal encerrado. Não reconhece direito a crédito, pagamento ou compensação entre tributos."),
          _createElementVNode("div", { class: "toolbar" }, [_createElementVNode("button", {
            type: "button",
            onClick: newAssessmentAdjustment
          }, "Novo ajuste manual de apuração", 8, ["onClick"]), _createElementVNode("button", {
            type: "button",
            onClick: loadAssessmentAdjustments,
            disabled: busy||!cycle
          }, "Consultar saldos de origem e histórico", 8, ["onClick", "disabled"])]),
          (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(balanceSources, (source) => {
            return (_openBlock(), _createElementBlock("article", {
              class: "inset",
              key: source.assessment_id+':'+source.component_key+':'+source.revenue_code
            }, [_createElementVNode("b", null, _toDisplayString(source.competence) + " · " + _toDisplayString(source.component_key) + " · receita " + _toDisplayString(source.revenue_code||'não informada'), 1), (source.blocker)
              ? (_openBlock(), _createElementBlock("p", {
                  key: 0,
                  class: "error"
                }, _toDisplayString(source.blocker), 1))
              : (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [_createElementVNode("p", null, "Saldo de origem " + _toDisplayString(source.balance) + " · reservado " + _toDisplayString(source.reserved) + " · disponível " + _toDisplayString(source.available) + " · natureza " + _toDisplayString(source.effect), 1), _createElementVNode("button", {
                  type: "button",
                  onClick: $event => (selectBalanceSource(source)),
                  disabled: busy||Number(source.available)<=0
                }, "Preparar transporte deste saldo", 8, ["onClick", "disabled"])], 64))]))
          }), 128)),
          _createElementVNode("form", {
            onSubmit: _withModifiers(previewAssessmentAdjustment, ["prevent"]),
            onInput: $event => {adjustmentPreview=null;adjustmentConfirmed=false}
          }, [
            _createElementVNode("h3", null, _toDisplayString(adjustmentForm.kind==='transporte'?'Transporte explícito de saldo':'Ajuste manual da apuração'), 1),
            (adjustmentForm.kind==='transporte')
              ? (_openBlock(), _createElementBlock("p", { key: 0 }, "Apuração de origem #" + _toDisplayString(adjustmentForm.source_assessment_id) + ". Valor a transportar deve ser declarado; não é preenchido pelo saldo disponível.", 1))
              : _createCommentVNode("", true),
            _createElementVNode("div", { class: "grid" }, [
              _createElementVNode("label", null, [_createTextVNode("Data do ajuste de apuração"), _withDirectives(_createElementVNode("input", {
                type: "date",
                "onUpdate:modelValue": $event => ((adjustmentForm.date) = $event),
                required: ""
              }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, adjustmentForm.date]])]),
              _createElementVNode("label", null, [_createTextVNode("Componente do ajuste de apuração"), _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": $event => ((adjustmentForm.component_key) = $event),
                readonly: adjustmentForm.kind==='transporte',
                placeholder: "ICMS ou FCP:IDENTIFICADOR",
                required: ""
              }, null, 8, ["onUpdate:modelValue", "readonly"]), [[_vModelText, adjustmentForm.component_key]])]),
              _createElementVNode("label", null, [_createTextVNode("Receita do ajuste de apuração"), _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": $event => ((adjustmentForm.revenue_code) = $event),
                readonly: adjustmentForm.kind==='transporte'
              }, null, 8, ["onUpdate:modelValue", "readonly"]), [[_vModelText, adjustmentForm.revenue_code]])]),
              _createElementVNode("label", null, [_createTextVNode("Efeito do ajuste de apuração"), _withDirectives(_createElementVNode("select", {
                "aria-label": "Efeito do ajuste de apuração",
                "onUpdate:modelValue": $event => ((adjustmentForm.effect) = $event),
                disabled: adjustmentForm.kind==='transporte',
                required: ""
              }, [_createElementVNode("option", { value: "" }, "Selecione explicitamente"), _createElementVNode("option", { value: "debito" }, "Débito declarado"), _createElementVNode("option", { value: "credito" }, "Crédito declarado")], 8, ["onUpdate:modelValue", "disabled"]), [[_vModelSelect, adjustmentForm.effect]])]),
              _createElementVNode("label", null, [_createTextVNode("Valor do ajuste de apuração"), _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": $event => ((adjustmentForm.amount) = $event),
                inputmode: "decimal",
                required: ""
              }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, adjustmentForm.amount]])]),
              _createElementVNode("label", null, [_createTextVNode("Descrição do ajuste de apuração"), _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": $event => ((adjustmentForm.description) = $event),
                required: ""
              }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, adjustmentForm.description]])]),
              _createElementVNode("label", null, [_createTextVNode("Referência que autoriza o ajuste ou transporte"), _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": $event => ((adjustmentForm.reference) = $event),
                required: ""
              }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, adjustmentForm.reference]])])
            ]),
            _createElementVNode("button", { disabled: busy||!cycle }, "Conferir prévia do ajuste", 8, ["disabled"])
          ], 40, ["onSubmit", "onInput"]),
          adjustmentPreview
            ? (_openBlock(), _createElementBlock("div", {
                key: 0,
                class: "inset"
              }, [
                _createElementVNode("h3", null, "Prévia do ajuste de apuração"),
                _createElementVNode("p", null, _toDisplayString(adjustmentPreview.snapshot.spec.component_key) + " · " + _toDisplayString(adjustmentPreview.snapshot.spec.effect) + " · " + _toDisplayString(adjustmentPreview.snapshot.spec.amount), 1),
                (adjustmentPreview.snapshot.capacity)
                  ? (_openBlock(), _createElementBlock("p", { key: 0 }, "Disponível na conferência: " + _toDisplayString(adjustmentPreview.snapshot.capacity.available) + ". Nenhuma reserva foi feita nesta prévia.", 1))
                  : _createCommentVNode("", true),
                _createElementVNode("details", null, [_createElementVNode("summary", null, "Memória da prévia do ajuste"), _createElementVNode("pre", null, _toDisplayString(JSON.stringify(adjustmentPreview.snapshot,null,2)), 1)])
              ]))
            : _createCommentVNode("", true),
          _createElementVNode("label", null, [_createTextVNode("Motivo do ajuste ou cancelamento"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((adjustmentReason) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, adjustmentReason]])]),
          _createElementVNode("label", null, [_createTextVNode("Referência da conferência do ajuste"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((adjustmentReviewReference) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, adjustmentReviewReference]])]),
          _createElementVNode("label", null, [_withDirectives(_createElementVNode("input", {
            type: "checkbox",
            "onUpdate:modelValue": $event => ((adjustmentConfirmed) = $event)
          }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, adjustmentConfirmed]]), _createTextVNode(" Conferi origem, valor, natureza, autorização e efeitos do ajuste ou cancelamento, sem presumir direito a crédito")]),
          adjustmentPreview
            ? (_openBlock(), _createElementBlock("button", {
                key: 1,
                type: "button",
                onClick: applyAssessmentAdjustment,
                disabled: busy||!adjustmentConfirmed
              }, "Aprovar ajuste de apuração", 8, ["onClick", "disabled"]))
            : _createCommentVNode("", true),
          (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(adjustmentHistory, (row) => {
            return (_openBlock(), _createElementBlock("article", {
              class: "inset",
              key: row.id,
              "data-assessment-adjustment": row.id
            }, [
              _createElementVNode("b", null, "#" + _toDisplayString(row.id) + " · " + _toDisplayString(row.snapshot.data.description) + " · " + _toDisplayString(row.state) + " · v" + _toDisplayString(row.version), 1),
              _createElementVNode("p", null, _toDisplayString(row.snapshot.data.component_key) + " · " + _toDisplayString(row.snapshot.data.effect) + " · " + _toDisplayString(row.snapshot.data.amount) + " · " + _toDisplayString(row.snapshot.data.kind) + " · " + _toDisplayString(row.current?'versão atual':'histórico preservado'), 1),
              (row.current&&row.state==='aprovada')
                ? (_openBlock(), _createElementBlock("button", {
                    key: 0,
                    type: "button",
                    onClick: $event => (cancelAssessmentAdjustment(row)),
                    disabled: busy||!adjustmentConfirmed
                  }, "Cancelar ajuste em nova versão", 8, ["onClick", "disabled"]))
                : _createCommentVNode("", true),
              _createElementVNode("details", null, [_createElementVNode("summary", null, "Evidência do ajuste"), _createElementVNode("pre", null, _toDisplayString(JSON.stringify(row,null,2)), 1)])
            ], 8, ["data-assessment-adjustment"]))
          }), 128))
        ]),
        _createElementVNode("article", { class: "inset" }, [
          _createElementVNode("h2", null, "Apuração parametrizada da competência"),
          _createElementVNode("p", null, "Soma automaticamente fatos escriturados pelos efeitos declarados nas regras. Valores informados são preservados. O saldo é aritmético: não gera guia, vencimento, crédito legal ou compensação automática. CBS/IBS permanecem fora do cálculo."),
          _createElementVNode("button", {
            onClick: previewAssessment,
            disabled: busy||!cycle
          }, "Gerar prévia da apuração", 8, ["onClick", "disabled"]),
          _createElementVNode("label", null, [_createTextVNode("Motivo da apuração ou validação"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((assessmentReason) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, assessmentReason]])]),
          _createElementVNode("label", null, [_withDirectives(_createElementVNode("input", {
            type: "checkbox",
            "onUpdate:modelValue": $event => ((assessmentConfirmed) = $event)
          }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, assessmentConfirmed]]), _createTextVNode(" Conferi fatos, regras, vigência, tabelas, bases, efeitos e memória da apuração")]),
          assessmentPreview
            ? (_openBlock(), _createElementBlock("div", { key: 0 }, [
                (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(assessmentPreview.snapshot.blockers, (blocker) => {
                  return (_openBlock(), _createElementBlock("p", { class: "error" }, _toDisplayString(blocker), 1))
                }), 256)),
                _createVNode(_component_data_table, {
                  rows: assessmentPreview.snapshot.totals,
                  columns: {tax:'Tributo',component_key:'Componente declarado',revenue_code:'Receita declarada',debito:'Débitos',credito:'Créditos',informativo:'Informativo',saldo_antes_ajustes:'Antes dos ajustes',ajustes_debito:'Ajustes débito',ajustes_credito:'Ajustes crédito',saldo_aritmetico:'Saldo aritmético'}
                }, null, 8, ["rows", "columns"]),
                (assessmentPreview.snapshot.grossup_groups)
                  ? (_openBlock(), _createBlock(_component_data_table, {
                      key: 0,
                      rows: assessmentPreview.snapshot.grossup_groups,
                      columns: {operation_id:'Operação',item_id:'Item',components:'Grupo por dentro',grossed_base:'Base bruta',rounded_tax_sum:'Tributos',residual:'Diferença',residual_policy:'Política'}
                    }, null, 8, ["rows", "columns"]))
                  : _createCommentVNode("", true),
                _createElementVNode("details", null, [_createElementVNode("summary", null, "Memória da prévia"), _createElementVNode("pre", null, _toDisplayString(JSON.stringify(assessmentPreview.snapshot,null,2)), 1)]),
                _createElementVNode("button", {
                  onClick: saveAssessment,
                  disabled: busy
                }, "Preservar versão da apuração", 8, ["onClick", "disabled"])
              ]))
            : _createCommentVNode("", true),
          (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(taxAssessments, (row) => {
            return (_openBlock(), _createElementBlock("article", {
              key: row.id,
              class: "inset"
            }, [
              _createElementVNode("b", null, "Apuração v" + _toDisplayString(row.version) + " · " + _toDisplayString(row.state), 1),
              _createElementVNode("p", { class: "tax-fingerprint" }, _toDisplayString(row.snapshot_hash), 1),
              _createVNode(_component_data_table, {
                rows: row.snapshot.totals,
                columns: {tax:'Tributo',component_key:'Componente declarado',revenue_code:'Receita',debito:'Débitos',credito:'Créditos',informativo:'Informativo',saldo_antes_ajustes:'Antes dos ajustes',ajustes_debito:'Ajustes débito',ajustes_credito:'Ajustes crédito',saldo_aritmetico:'Saldo aritmético'}
              }, null, 8, ["rows", "columns"]),
              _createElementVNode("button", {
                onClick: $event => (validateAssessment(row)),
                disabled: busy||!assessmentConfirmed||row.state==='validada'
              }, "Validar apuração conferida", 8, ["onClick", "disabled"]),
              _createElementVNode("button", { onClick: $event => (downloadAssessment(row)) }, "Baixar memória JSON", 8, ["onClick"])
            ]))
          }), 128))
        ])
      ], 512), [[_vShow, page==='tax']]),
      _withDirectives(_createElementVNode("section", { class: "card" }, [
        _createElementVNode("h1", null, "Encerramento da competência"),
        _createElementVNode("h2", null, "Encerramento independente por módulo"),
        _createElementVNode("p", null, "Feche fiscal e contábil separadamente por cliente e mês. Operações que produzem efeitos nos dois módulos exigem ambos abertos. A recepção continua disponível; organizar e escriturar respeitam os bloqueios. Quando houver regras ou apuração parametrizada, valide a memória atual em Tributação e apuração. Sem parametrização automática, registre a referência da conferência externa."),
        _createElementVNode("label", null, [_createTextVNode("Motivo do controle por módulo"), _withDirectives(_createElementVNode("input", {
          "onUpdate:modelValue": $event => ((moduleClosing.reason) = $event),
          maxlength: "2000"
        }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, moduleClosing.reason]])]),
        _createElementVNode("label", null, [_createTextVNode("Referência da conferência da apuração"), _withDirectives(_createElementVNode("input", {
          "onUpdate:modelValue": $event => ((moduleClosing.evidence_reference) = $event),
          maxlength: "1000"
        }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, moduleClosing.evidence_reference]])]),
        (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(moduleStates, (row) => {
          return (_openBlock(), _createElementBlock("article", {
            key: row.state.module,
            "data-module": row.state.module,
            class: "inset"
          }, [
            _createElementVNode("h3", null, _toDisplayString(row.state.module==='fiscal'?'Fiscal':'Contábil') + " · " + _toDisplayString(row.state.competence) + " · " + _toDisplayString(row.state.state), 1),
            (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(row.blockers, (blocker) => {
              return (_openBlock(), _createElementBlock("p", null, _toDisplayString(blocker), 1))
            }), 256)),
            (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(row.required_checks, (key) => {
              return (_openBlock(), _createElementBlock("label", null, [_withDirectives(_createElementVNode("input", {
                type: "checkbox",
                "onUpdate:modelValue": $event => ((moduleClosing.checks[key]) = $event)
              }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, moduleClosing.checks[key]]]), _createTextVNode(" Conferido: " + _toDisplayString(({lancamentos:'lançamentos',livros:'livros',correcoes:'correções',apuracao:'apuração',saldos:'saldos'})[key]), 1)]))
            }), 256)),
            _createElementVNode("button", {
              onClick: $event => (closeModule(row)),
              disabled: busy||row.global_state!=='aberta'
            }, _toDisplayString(row.state.state==='encerrada'?'Reabrir':'Encerrar') + " " + _toDisplayString(row.state.module==='fiscal'?'fiscal':'contábil'), 9, ["onClick", "disabled"])
          ], 8, ["data-module"]))
        }), 128)),
        _createElementVNode("details", null, [
          _createElementVNode("summary", null, "Controle global anterior"),
          _createElementVNode("p", null, "Encerre depois de resolver documentos e versões pendentes e declarar a abertura. A reabertura mantém o histórico e exige motivo."),
          _createVNode(_component_data_table, {
            rows: overview?[overview.counts]:[],
            columns: {pending_documents:'Documentos pendentes',drafts:'Rascunhos',reviewed:'Conferidos não escriturados',posted:'Escriturados',rejected_inputs:'Origens rejeitadas',legacy_pending:'Rascunhos anteriores não retomados',open_forms:'Guias incompletas abertas'}
          }, null, 8, ["rows", "columns"]),
          _createElementVNode("form", { onSubmit: _withModifiers(closeCycle, ["prevent"]) }, [_createElementVNode("label", null, [_createTextVNode("Motivo"), _withDirectives(_createElementVNode("input", {
            "onUpdate:modelValue": $event => ((closing.reason) = $event),
            required: ""
          }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, closing.reason]])]), _createElementVNode("label", null, [_withDirectives(_createElementVNode("input", {
            type: "checkbox",
            "onUpdate:modelValue": $event => ((closing.acknowledge_errors) = $event)
          }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, closing.acknowledge_errors]]), _createTextVNode(" Conferi e reconheço os arquivos rejeitados e rascunhos anteriores não retomados deste recorte")]), _createElementVNode("button", { disabled: busy||!cycle }, _toDisplayString(cycle?.state==='encerrada'?'Reabrir com motivo':'Encerrar competência'), 9, ["disabled"])], 40, ["onSubmit"])
        ])
      ], 512), [[_vShow, page==='closing']]),
      _withDirectives(_createElementVNode("section", { class: "card" }, [
        _createElementVNode("h1", null, "Histórico preservado e migração"),
        _createElementVNode("h2", null, "Guias encerradas deste operador"),
        (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(archivedTabs, (t) => {
          return (_openBlock(), _createElementBlock("article", { class: "inset" }, [_createElementVNode("b", null, _toDisplayString(t.title), 1), _createElementVNode("small", null, _toDisplayString(t.updated_at) + " · " + _toDisplayString(t.data.payload?.reference||'Rascunho preservado'), 1), _createElementVNode("button", {
            onClick: $event => (reopenTab(t)),
            disabled: busy
          }, "Reabrir guia", 8, ["onClick", "disabled"])]))
        }), 256)),
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
            key: 4,
            class: "empty"
          }, "Selecione ou cadastre uma empresa no portal para iniciar."))
        : (!cycle && !['imports','setup','chart'].includes(page))
          ? (_openBlock(), _createElementBlock("p", {
              key: 5,
              class: "empty"
            }, "Defina uma competência em Competências. A caixa de entrada já recebe arquivos."))
          : _createCommentVNode("", true)
    ], 8, ["aria-busy"]))
  }
};
