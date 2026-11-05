/* Template pré-compilado: não requer eval no navegador. */
var _Vue=Vue; var EscrituraRender=function render(_ctx, _cache) {
  with (_ctx) {
    const { openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, createElementVNode: _createElementVNode, createTextVNode: _createTextVNode, toDisplayString: _toDisplayString, vModelText: _vModelText, withDirectives: _withDirectives, Fragment: _Fragment, withModifiers: _withModifiers, renderList: _renderList, normalizeClass: _normalizeClass, vShow: _vShow, resolveComponent: _resolveComponent, createVNode: _createVNode, vModelSelect: _vModelSelect, vModelCheckbox: _vModelCheckbox } = _Vue

    const _component_data_table = _resolveComponent("data-table")

    return (_openBlock(), _createElementBlock("div", {
      class: "app-root",
      "aria-busy": busy
    }, [(!ready)
      ? (_openBlock(), _createElementBlock("div", {
          key: 0,
          class: "loading"
        }, "Preparando seu ambiente…"))
      : (!user)
        ? (_openBlock(), _createElementBlock("div", {
            key: 1,
            class: "auth-layout"
          }, [_createElementVNode("section", { class: "auth-intro" }, [_createElementVNode("a", {
            class: "brand",
            href: "/public"
          }, [_createElementVNode("img", {
            src: "/assets/symbol.svg",
            alt: ""
          }), _createElementVNode("strong", null, [_createTextVNode("Escritura"), _createElementVNode("span", null, "ORGANIZAÇÃO CONTÁBIL")])]), _createElementVNode("div", { class: "auth-copy" }, [
            _createElementVNode("p", { class: "eyebrow" }, "CLAREZA EM CADA ETAPA"),
            _createElementVNode("h1", null, [_createTextVNode("Da origem ao registro."), _createElementVNode("br"), _createTextVNode("Uma história completa.")]),
            _createElementVNode("p", null, "Documentos, conferências e decisões conectados em um só ambiente."),
            _createElementVNode("div", { class: "auth-features" }, [_createElementVNode("span", null, [_createTextVNode("01 "), _createElementVNode("b", null, "Organize as origens")]), _createElementVNode("span", null, [_createTextVNode("02 "), _createElementVNode("b", null, "Concilie com contexto")]), _createElementVNode("span", null, [_createTextVNode("03 "), _createElementVNode("b", null, "Preserve cada decisão")])])
          ]), _createElementVNode("footer", null, "Escritura · Seu trabalho, com rastreabilidade.")]), _createElementVNode("section", { class: "auth-panel" }, [_createElementVNode("div", { class: "auth-form" }, [
            _createElementVNode("p", { class: "eyebrow" }, _toDisplayString(!configured?'PRIMEIRO ACESSO':authMode==='forgot'?'RECUPERAR ACESSO':authMode==='reset'?'NOVA SENHA':'BEM-VINDO AO ESCRITURA'), 1),
            _createElementVNode("h2", null, _toDisplayString(!configured?'Configure seu ambiente':challenge?'Verifique sua identidade':authMode==='forgot'?'Esqueceu sua senha?':authMode==='reset'?'Redefina sua senha':'Acesse sua conta'), 1),
            _createElementVNode("p", { class: "muted" }, _toDisplayString(!configured?'Cadastre o administrador da instalação.':challenge?'Informe o código do autenticador ou um código de recuperação.':'Use suas credenciais para continuar.'), 1),
            error
              ? (_openBlock(), _createElementBlock("div", {
                  key: 0,
                  class: "alert error",
                  role: "alert"
                }, _toDisplayString(error), 1))
              : _createCommentVNode("", true),
            notice
              ? (_openBlock(), _createElementBlock("div", {
                  key: 1,
                  class: "alert success",
                  role: "status"
                }, _toDisplayString(notice), 1))
              : _createCommentVNode("", true),
            _createElementVNode("form", { onSubmit: _withModifiers(submitAuth, ["prevent"]) }, [
              (!configured)
                ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [_createElementVNode("label", { class: "field" }, [_createTextVNode("Chave de instalação"), _withDirectives(_createElementVNode("input", {
                    "onUpdate:modelValue": $event => ((auth.token) = $event),
                    type: "password",
                    required: "",
                    autocomplete: "off"
                  }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, auth.token]])]), _createElementVNode("label", { class: "field" }, [_createTextVNode("Nome do administrador"), _withDirectives(_createElementVNode("input", {
                    "onUpdate:modelValue": $event => ((auth.name) = $event),
                    required: "",
                    autocomplete: "name"
                  }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, auth.name]])])], 64))
                : _createCommentVNode("", true),
              (!challenge && authMode!=='reset')
                ? (_openBlock(), _createElementBlock("label", {
                    key: 1,
                    class: "field"
                  }, [_createTextVNode("E-mail"), _withDirectives(_createElementVNode("input", {
                    "onUpdate:modelValue": $event => ((auth.email) = $event),
                    type: "email",
                    required: "",
                    autocomplete: "username",
                    placeholder: "voce@empresa.com.br"
                  }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, auth.email]])]))
                : _createCommentVNode("", true),
              (!challenge && authMode!=='forgot')
                ? (_openBlock(), _createElementBlock("label", {
                    key: 2,
                    class: "field"
                  }, [_createTextVNode(_toDisplayString(authMode==='reset'?'Nova senha':'Senha'), 1), _withDirectives(_createElementVNode("input", {
                    "onUpdate:modelValue": $event => ((auth.password) = $event),
                    type: "password",
                    required: "",
                    minlength: !configured||authMode==='reset'?12:1,
                    maxlength: "128",
                    autocomplete: authMode==='reset'||!configured?'new-password':'current-password'
                  }, null, 8, ["onUpdate:modelValue", "minlength", "autocomplete"]), [[_vModelText, auth.password]])]))
                : _createCommentVNode("", true),
              (challenge || authMode==='reset')
                ? (_openBlock(), _createElementBlock("label", {
                    key: 3,
                    class: "field"
                  }, [_createTextVNode(_toDisplayString(challenge?'Código de verificação':'Código 2FA ou recuperação, se habilitado'), 1), _withDirectives(_createElementVNode("input", {
                    "onUpdate:modelValue": $event => ((auth.code) = $event),
                    required: !!challenge,
                    autocomplete: "one-time-code",
                    maxlength: "40"
                  }, null, 8, ["onUpdate:modelValue", "required"]), [[_vModelText, auth.code]])]))
                : _createCommentVNode("", true),
              _createElementVNode("button", {
                class: "btn primary full",
                disabled: busy
              }, [_createTextVNode(_toDisplayString(busy?'Aguarde…':!configured?'Concluir configuração':challenge?'Verificar e entrar':authMode==='forgot'?'Enviar instruções':authMode==='reset'?'Salvar nova senha':'Entrar no ambiente') + " ", 1), _createElementVNode("span", null, "→")], 8, ["disabled"])
            ], 40, ["onSubmit"]),
            configured
              ? (_openBlock(), _createElementBlock("button", {
                  key: 2,
                  class: "link-button auth-help",
                  onClick: $event => {authMode=authMode==='login'?'forgot':'login';challenge='';error='';notice=''}
                }, _toDisplayString(authMode==='login'?'Esqueci minha senha':'Voltar para o login'), 9, ["onClick"]))
              : _createCommentVNode("", true),
            _createElementVNode("p", { class: "auth-note" }, "Acesso individual · Sessões protegidas · Histórico de operações")
          ])])]))
        : (_openBlock(), _createElementBlock("div", {
            key: 2,
            class: "workspace"
          }, [
            _createElementVNode("a", {
              class: "skip",
              href: "#content"
            }, "Ir para o conteúdo"),
            menuOpen
              ? (_openBlock(), _createElementBlock("button", {
                  key: 0,
                  class: "sidebar-shade",
                  "aria-label": "Fechar menu",
                  onClick: $event => (menuOpen=false)
                }, null, 8, ["onClick"]))
              : _createCommentVNode("", true),
            _createElementVNode("aside", { class: _normalizeClass(["sidebar", {visible:menuOpen}]) }, [
              _createElementVNode("a", {
                class: "brand",
                href: "#/dashboard"
              }, [_createElementVNode("img", {
                src: "/assets/symbol.svg",
                alt: ""
              }), _createElementVNode("strong", null, [_createTextVNode("Escritura"), _createElementVNode("span", null, "ORGANIZAÇÃO CONTÁBIL")])]),
              _createElementVNode("div", { class: "workspace-label" }, [_createElementVNode("span", { class: "dot" }), _createTextVNode(" Ambiente de trabalho")]),
              _createElementVNode("div", { class: "sidebar-scroll" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(menuGroups, (group) => {
                return (_openBlock(), _createElementBlock(_Fragment, { key: group.label }, [_createElementVNode("p", { class: "sidebar-label" }, _toDisplayString(group.label), 1), _createElementVNode("nav", { "aria-label": group.label }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(group.items, (item) => {
                  return (_openBlock(), _createElementBlock("a", {
                    key: item.id,
                    href: '#/'+item.id,
                    class: _normalizeClass({active:page===item.id}),
                    "aria-current": page===item.id?'page':undefined,
                    onClick: $event => (menuOpen=false)
                  }, [_createElementVNode("span", {
                    class: "nav-icon",
                    "aria-hidden": "true"
                  }, _toDisplayString(item.icon), 1), _createTextVNode(_toDisplayString(item.label), 1), (page===item.id)
                    ? (_openBlock(), _createElementBlock("span", {
                        key: 0,
                        class: "nav-mark",
                        "aria-hidden": "true"
                      }, "•"))
                    : _createCommentVNode("", true)], 10, ["href", "aria-current", "onClick"]))
                }), 128))], 8, ["aria-label"])], 64))
              }), 128))]),
              _createElementVNode("div", { class: "sidebar-bottom" }, [_createElementVNode("div", { class: "avatar" }, _toDisplayString(initials), 1), _createElementVNode("div", null, [_createElementVNode("strong", null, _toDisplayString(user.name), 1), _createElementVNode("small", null, _toDisplayString(user.role_name), 1)]), _createElementVNode("button", {
                class: "icon-button",
                onClick: logout,
                title: "Sair",
                "aria-label": "Sair"
              }, "↗", 8, ["onClick"])])
            ], 2),
            _createElementVNode("div", { class: "main-area" }, [_createElementVNode("header", { class: "topbar" }, [_createElementVNode("div", { class: "actions" }, [_createElementVNode("button", {
              class: "icon-button mobile-menu",
              onClick: $event => (menuOpen=!menuOpen),
              "aria-label": "Abrir menu"
            }, "☰", 8, ["onClick"]), _createElementVNode("span", { class: "breadcrumb" }, [
              _createTextVNode("Ambiente "),
              _createElementVNode("span", null, "/"),
              _createTextVNode(),
              _createElementVNode("b", null, _toDisplayString(pageTitle), 1)
            ])]), _createElementVNode("div", { class: "actions" }, [_createElementVNode("label", { class: "menu-search" }, [_createElementVNode("span", null, "⌕"), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((menuSearch) = $event),
              placeholder: "Buscar no menu",
              "aria-label": "Buscar no menu"
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, menuSearch]])]), _createElementVNode("span", { class: "environment-badge" }, [_createElementVNode("span", { class: "dot" }), _createTextVNode(" Conectado")]), _createElementVNode("a", {
              href: "#/security",
              class: "avatar small-avatar",
              title: user.name
            }, _toDisplayString(initials), 9, ["title"])])]), _createElementVNode("main", {
              id: "content",
              tabindex: "-1",
              class: _normalizeClass({'operating':workspacePages.includes(page)})
            }, [
              _createElementVNode("div", { class: "page-heading" }, [_createElementVNode("div", null, [_createElementVNode("p", { class: "eyebrow" }, _toDisplayString(page==='client'?'PORTAL DO CLIENTE':'ESCRITURA / '+pageTitle.toUpperCase()), 1), _createElementVNode("h1", null, _toDisplayString(pageTitle), 1), _createElementVNode("p", { class: "muted" }, _toDisplayString(pageSubtitle), 1)]), _createElementVNode("button", {
                class: "btn secondary",
                onClick: loadPage,
                disabled: busy
              }, "↻ Atualizar", 8, ["onClick", "disabled"])]),
              error
                ? (_openBlock(), _createElementBlock("div", {
                    key: 0,
                    class: "alert error",
                    role: "alert"
                  }, [_createTextVNode(_toDisplayString(error), 1), _createElementVNode("button", {
                    onClick: $event => (error=''),
                    "aria-label": "Fechar aviso"
                  }, "×", 8, ["onClick"])]))
                : _createCommentVNode("", true),
              notice
                ? (_openBlock(), _createElementBlock("div", {
                    key: 1,
                    class: "alert success",
                    role: "status"
                  }, [_createTextVNode(_toDisplayString(notice), 1), _createElementVNode("button", {
                    onClick: $event => (notice=''),
                    "aria-label": "Fechar aviso"
                  }, "×", 8, ["onClick"])]))
                : _createCommentVNode("", true),
              (openWorkspaceTabs.length)
                ? (_openBlock(), _createElementBlock("nav", {
                    key: 2,
                    class: "activity-tabs",
                    "aria-label": "Atividades abertas"
                  }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(openWorkspaceTabs, (tab) => {
                    return (_openBlock(), _createElementBlock("div", {
                      key: tab.id,
                      class: _normalizeClass({selected:page===tab.id})
                    }, [_createElementVNode("a", {
                      href: '#/'+tab.id,
                      "aria-label": 'Atividade '+tab.label,
                      "aria-current": page===tab.id?'page':undefined
                    }, [_createElementVNode("span", { "aria-hidden": "true" }, _toDisplayString(tab.icon), 1), _createTextVNode(" " + _toDisplayString(tab.label), 1)], 8, ["href", "aria-label", "aria-current"]), _createElementVNode("button", {
                      onClick: $event => (closeWorkspaceTab(tab.id)),
                      "aria-label": 'Fechar atividade '+tab.label,
                      title: "Fechar atividade; o rascunho permanece disponível"
                    }, "×", 8, ["onClick", "aria-label"])], 2))
                  }), 128))]))
                : _createCommentVNode("", true),
              _withDirectives(_createElementVNode("section", null, [_createElementVNode("div", { class: "welcome-banner" }, [_createElementVNode("div", null, [_createElementVNode("span", { class: "eyebrow" }, "SEU AMBIENTE, ORGANIZADO"), _createElementVNode("h2", null, "Bom trabalho, " + _toDisplayString(user.name.split(' ')[0]) + ".", 1), _createElementVNode("p", null, "Acompanhe suas empresas e continue de onde parou.")]), _createElementVNode("img", {
                src: "/assets/symbol.svg",
                alt: "",
                width: "88"
              })]), _createElementVNode("div", { class: "stats" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(metrics, (metric) => {
                return (_openBlock(), _createElementBlock("article", {
                  key: metric.key,
                  class: "stat-card"
                }, [
                  _createElementVNode("span", null, _toDisplayString(metric.label), 1),
                  _createElementVNode("strong", null, _toDisplayString(dashboard.metrics[metric.key]||0), 1),
                  _createElementVNode("small", null, _toDisplayString(metric.help), 1),
                  _createElementVNode("i", null, _toDisplayString(metric.icon), 1)
                ]))
              }), 128))]), _createElementVNode("div", { class: "dashboard-grid" }, [_createElementVNode("section", { class: "panel" }, [_createElementVNode("header", { class: "panel-header" }, [_createElementVNode("div", null, [_createElementVNode("h2", null, "Empresas do seu ambiente"), _createElementVNode("p", { class: "muted small" }, "Acesso conforme o seu perfil")]), (can('companies.manage'))
                ? (_openBlock(), _createElementBlock("a", {
                    key: 0,
                    href: "#/companies",
                    class: "link-button"
                  }, "Gerenciar →"))
                : _createCommentVNode("", true)]), (!dashboard.companies.length)
                ? (_openBlock(), _createElementBlock("div", {
                    key: 0,
                    class: "empty"
                  }, [
                    _createElementVNode("span", null, "▧"),
                    _createElementVNode("h3", null, "Comece pela primeira empresa"),
                    _createElementVNode("p", null, "Cadastre a empresa e defina as competências para organizar os documentos."),
                    (can('companies.manage'))
                      ? (_openBlock(), _createElementBlock("a", {
                          key: 0,
                          href: "#/companies",
                          class: "btn primary"
                        }, "Cadastrar empresa"))
                      : _createCommentVNode("", true)
                  ]))
                : (_openBlock(), _createElementBlock("div", {
                    key: 1,
                    class: "company-list"
                  }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(dashboard.companies, (c) => {
                    return (_openBlock(), _createElementBlock("button", {
                      key: c.id,
                      onClick: $event => (openCompany(c))
                    }, [
                      _createElementVNode("span", { class: "company-icon" }, "▥"),
                      _createElementVNode("span", null, [_createElementVNode("b", null, _toDisplayString(c.name), 1), _createElementVNode("small", null, _toDisplayString(c.cnpj||'CNPJ não informado'), 1)]),
                      _createElementVNode("span", { class: "badge" }, "Disponível"),
                      _createElementVNode("span", null, "→")
                    ], 8, ["onClick"]))
                  }), 128))]))]), _createElementVNode("section", { class: "panel next-steps" }, [_createElementVNode("p", { class: "eyebrow" }, "PRÓXIMOS PASSOS"), _createElementVNode("h2", null, "Um fluxo que faz sentido."), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(nextSteps, (step, i) => {
                return (_openBlock(), _createElementBlock("a", {
                  key: step.title,
                  href: step.href
                }, [_createElementVNode("span", { class: "step-number" }, _toDisplayString(i+1), 1), _createElementVNode("span", null, [_createElementVNode("b", null, _toDisplayString(step.title), 1), _createElementVNode("small", null, _toDisplayString(step.text), 1)]), _createElementVNode("span", null, "→")], 8, ["href"]))
              }), 128))])])], 512), [[_vShow, page==='dashboard']]),
              _withDirectives(_createElementVNode("section", null, [_createElementVNode("div", { class: "panel padded" }, [_createElementVNode("h2", null, "Nova empresa"), _createElementVNode("form", {
                onSubmit: _withModifiers(saveCompany, ["prevent"]),
                class: "form-grid"
              }, [
                _createElementVNode("label", { class: "field" }, [_createTextVNode("Nome"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((companyForm.name) = $event),
                  required: "",
                  maxlength: "200"
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, companyForm.name]])]),
                _createElementVNode("label", { class: "field" }, [_createTextVNode("CNPJ"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((companyForm.cnpj) = $event),
                  maxlength: "18"
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, companyForm.cnpj]])]),
                _createElementVNode("label", { class: "field" }, [_createTextVNode("Código Prosoft (opcional)"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((companyForm.prosoft_company_code) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, companyForm.prosoft_company_code]])]),
                _createElementVNode("label", { class: "field" }, [_createTextVNode("Plano Prosoft (opcional)"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((companyForm.prosoft_plan_code) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, companyForm.prosoft_plan_code]])]),
                _createElementVNode("div", { class: "wide" }, [_createElementVNode("button", {
                  class: "btn primary",
                  disabled: busy
                }, "Cadastrar empresa", 8, ["disabled"])])
              ], 40, ["onSubmit"])]), _createElementVNode("div", { class: "panel spaced" }, [_createVNode(_component_data_table, {
                rows: dashboard.companies,
                columns: {name:'Empresa',cnpj:'CNPJ',prosoft_company_code:'Código Prosoft',prosoft_plan_code:'Plano'}
              }, null, 8, ["rows", "columns"])])], 512), [[_vShow, page==='companies']]),
              _withDirectives(_createElementVNode("section", null, [_createElementVNode("div", { class: "panel" }, [_createElementVNode("header", { class: "panel-header" }, [_createElementVNode("h2", null, "Usuários e acessos"), _createElementVNode("button", {
                class: "btn primary",
                onClick: $event => (editUser())
              }, "+ Novo usuário", 8, ["onClick"])]), _createElementVNode("div", { class: "table-scroll" }, [_createElementVNode("table", null, [_createElementVNode("thead", null, [_createElementVNode("tr", null, [
                _createElementVNode("th", null, "Usuário"),
                _createElementVNode("th", null, "Perfil"),
                _createElementVNode("th", null, "Empresas"),
                _createElementVNode("th", null, "2FA"),
                _createElementVNode("th", null, "Situação"),
                _createElementVNode("th")
              ])]), _createElementVNode("tbody", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(users, (u) => {
                return (_openBlock(), _createElementBlock("tr", { key: u.id }, [
                  _createElementVNode("td", null, [_createElementVNode("b", null, _toDisplayString(u.name), 1), _createElementVNode("small", null, _toDisplayString(u.email), 1)]),
                  _createElementVNode("td", null, _toDisplayString(u.role_name), 1),
                  _createElementVNode("td", null, _toDisplayString(u.role==='admin'?'Todas':u.companies.length), 1),
                  _createElementVNode("td", null, _toDisplayString(u.mfa_enabled?'Ativo':'Não habilitado'), 1),
                  _createElementVNode("td", null, [_createElementVNode("span", { class: _normalizeClass(["badge", {warning:!u.active}]) }, _toDisplayString(u.active?'Ativo':'Inativo'), 3)]),
                  _createElementVNode("td", null, [_createElementVNode("button", {
                    class: "link-button",
                    onClick: $event => (editUser(u))
                  }, "Editar", 8, ["onClick"])])
                ]))
              }), 128))])])])])], 512), [[_vShow, page==='users']]),
              _withDirectives(_createElementVNode("section", null, [_createElementVNode("div", { class: "panel" }, [_createElementVNode("header", { class: "panel-header" }, [_createElementVNode("h2", null, "Perfis de acesso"), _createElementVNode("button", {
                class: "btn primary",
                onClick: $event => {roleForm={name:'',permissions:[]};dialog='role'}
              }, "+ Novo perfil", 8, ["onClick"])]), _createElementVNode("div", { class: "role-grid" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(roles, (role) => {
                return (_openBlock(), _createElementBlock("article", { key: role.id }, [
                  _createElementVNode("h3", null, _toDisplayString(role.name), 1),
                  _createElementVNode("p", null, _toDisplayString(role.permissions.length) + " permissões", 1),
                  _createElementVNode("ul", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(role.permissions, (permission) => {
                    return (_openBlock(), _createElementBlock("li", { key: permission }, _toDisplayString(permissions[permission]), 1))
                  }), 128))]),
                  (!['admin','accountant','reviewer','client','reader'].includes(role.id))
                    ? (_openBlock(), _createElementBlock("button", {
                        key: 0,
                        class: "link-button",
                        onClick: $event => {roleForm=structuredCopy(role);dialog='role'}
                      }, "Editar perfil", 8, ["onClick"]))
                    : _createCommentVNode("", true)
                ]))
              }), 128))])])], 512), [[_vShow, page==='roles']]),
              _withDirectives(_createElementVNode("section", null, [_createElementVNode("div", { class: "panel padded" }, [
                _createElementVNode("label", { class: "field" }, [_createTextVNode("Empresa"), _withDirectives(_createElementVNode("select", {
                  "aria-label": "Empresa",
                  "onUpdate:modelValue": $event => ((clientCompany) = $event),
                  onChange: loadClient
                }, [_createElementVNode("option", { value: "" }, "Selecione"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(dashboard.companies, (c) => {
                  return (_openBlock(), _createElementBlock("option", {
                    value: String(c.id),
                    key: c.id
                  }, _toDisplayString(c.name), 9, ["value"]))
                }), 128))], 40, ["onUpdate:modelValue", "onChange"]), [[_vModelSelect, clientCompany]])]),
                _createElementVNode("p", null, "Envie os documentos sem precisar definir competência ou plano. A organização e a escrituração serão feitas pela equipe responsável."),
                (can('client.upload'))
                  ? (_openBlock(), _createElementBlock("form", {
                      key: 0,
                      onSubmit: _withModifiers(uploadClient, ["prevent"]),
                      class: "upload-bar"
                    }, [_createElementVNode("label", { class: "field grow" }, [_createTextVNode("Arquivos"), _createElementVNode("input", {
                      type: "file",
                      accept: ".xml,.txt,.sped,.zip,.7z,.rar",
                      multiple: "",
                      onChange: $event => {uploadFile=Array.from($event.target.files);uploadAttempt=null},
                      required: ""
                    }, null, 40, ["onChange"])]), _createElementVNode("button", {
                      class: "btn primary",
                      disabled: busy||!clientCompany
                    }, "Receber arquivos", 8, ["disabled"])], 40, ["onSubmit"]))
                  : _createCommentVNode("", true),
                _createElementVNode("p", null, "Até 10 MiB por envio. ZIP integrado; 7z/RAR dependem do leitor da instalação e não estão disponíveis no Windows congelado atual."),
                _createVNode(_component_data_table, {
                  rows: clientInbox,
                  columns: {filename:'Origem',kind:'Tipo','evidence.state':'Situação','evidence.issues':'Pendências',created_at:'Recebido em'}
                }, null, 8, ["rows", "columns"])
              ])], 512), [[_vShow, page==='client']]),
              _withDirectives(_createElementVNode("section", { class: "panel padded" }, [
                _createElementVNode("h2", null, "Configurações do ambiente"),
                _createElementVNode("form", {
                  onSubmit: _withModifiers($event => (saveSettings('general')), ["prevent"]),
                  class: "form-grid"
                }, [_createElementVNode("label", { class: "field" }, [_createTextVNode("Nome de exibição"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((settings.general.display_name) = $event),
                  maxlength: "200"
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, settings.general.display_name]])]), _createElementVNode("label", { class: "field" }, [_createTextVNode("E-mail de suporte"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((settings.general.support_email) = $event),
                  type: "email"
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, settings.general.support_email]])]), _createElementVNode("div", { class: "wide" }, [_createElementVNode("button", {
                  class: "btn primary",
                  disabled: busy
                }, "Salvar configurações", 8, ["disabled"])])], 40, ["onSubmit"]),
                _createElementVNode("div", { class: "divider" }),
                _createElementVNode("h2", null, "Ordem dos menus"),
                _createElementVNode("p", { class: "muted" }, "As permissões de cada usuário continuam sendo aplicadas."),
                _createElementVNode("div", { class: "menu-editor" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(menuOrder, (id, i) => {
                  return (_openBlock(), _createElementBlock("div", { key: id }, [_createElementVNode("span", null, _toDisplayString(allMenu.find(m=>m.id===id)?.label||id), 1), _createElementVNode("button", {
                    class: "btn secondary small-button",
                    onClick: $event => (moveMenu(i,-1)),
                    disabled: i===0,
                    "aria-label": "Subir menu"
                  }, "↑", 8, ["onClick", "disabled"]), _createElementVNode("button", {
                    class: "btn secondary small-button",
                    onClick: $event => (moveMenu(i,1)),
                    disabled: i===menuOrder.length-1,
                    "aria-label": "Descer menu"
                  }, "↓", 8, ["onClick", "disabled"])]))
                }), 128))]),
                _createElementVNode("button", {
                  class: "btn primary",
                  onClick: $event => (saveSettings('menu')),
                  disabled: busy
                }, "Salvar ordem", 8, ["onClick", "disabled"])
              ], 512), [[_vShow, page==='settings']]),
              _withDirectives(_createElementVNode("section", null, [_createElementVNode("div", { class: "panel padded" }, [_createElementVNode("h2", null, "Entrega de e-mails"), _createElementVNode("p", { class: "muted" }, "Recuperação de senha e notificações transacionais."), _createElementVNode("form", {
                onSubmit: _withModifiers($event => (saveSettings('smtp')), ["prevent"]),
                class: "form-grid"
              }, [
                _createElementVNode("label", { class: "field" }, [_createTextVNode("Servidor SMTP"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((settings.smtp.host) = $event),
                  required: ""
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, settings.smtp.host]])]),
                _createElementVNode("label", { class: "field" }, [_createTextVNode("Porta"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((settings.smtp.port) = $event),
                  type: "number",
                  min: "1",
                  max: "65535",
                  required: ""
                }, null, 8, ["onUpdate:modelValue"]), [[
                  _vModelText,
                  settings.smtp.port,
                  void 0,
                  { number: true }
                ]])]),
                _createElementVNode("label", { class: "field" }, [_createTextVNode("Conexão"), _withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((settings.smtp.mode) = $event) }, [_createElementVNode("option", { value: "starttls" }, "STARTTLS"), _createElementVNode("option", { value: "ssl" }, "TLS direto")], 8, ["onUpdate:modelValue"]), [[_vModelSelect, settings.smtp.mode]])]),
                _createElementVNode("label", { class: "field" }, [_createTextVNode("Remetente"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((settings.smtp.sender) = $event),
                  type: "email",
                  required: ""
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, settings.smtp.sender]])]),
                _createElementVNode("label", { class: "field" }, [_createTextVNode("Usuário"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((settings.smtp.username) = $event),
                  autocomplete: "off"
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, settings.smtp.username]])]),
                _createElementVNode("label", { class: "field" }, [_createTextVNode("Senha"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((settings.smtp.password) = $event),
                  type: "password",
                  autocomplete: "new-password",
                  placeholder: settings.smtp.has_password?'Já configurada · deixe vazio para manter':'Senha SMTP'
                }, null, 8, ["onUpdate:modelValue", "placeholder"]), [[_vModelText, settings.smtp.password]])]),
                _createElementVNode("div", { class: "wide actions" }, [_createElementVNode("button", {
                  class: "btn primary",
                  disabled: busy
                }, "Salvar SMTP", 8, ["disabled"]), _createElementVNode("button", {
                  type: "button",
                  class: "btn secondary",
                  onClick: testEmail,
                  disabled: busy
                }, "Enviar teste para meu e-mail", 8, ["onClick", "disabled"])])
              ], 40, ["onSubmit"])]), _createElementVNode("div", { class: "panel spaced" }, [_createElementVNode("header", { class: "panel-header" }, [_createElementVNode("h2", null, "Fila de entrega")]), _createVNode(_component_data_table, {
                rows: mail,
                columns: {id:'ID',recipient:'Destinatário',status:'Situação',attempts:'Tentativas',error:'Diagnóstico'}
              }, null, 8, ["rows", "columns"])])], 512), [[_vShow, page==='email']]),
              _withDirectives(_createElementVNode("section", null, [_createElementVNode("div", { class: "two-col" }, [_createElementVNode("section", { class: "panel padded" }, [
                _createElementVNode("p", { class: "eyebrow" }, "PROTEÇÃO DA CONTA"),
                _createElementVNode("h2", null, "Autenticação em duas etapas"),
                _createElementVNode("p", { class: "muted" }, "Um código do autenticador complementa sua senha."),
                _createElementVNode("span", { class: _normalizeClass(["badge spaced", {warning:!user.mfa_enabled}]) }, _toDisplayString(user.mfa_enabled?'2FA habilitado':'2FA não habilitado'), 3),
                _createElementVNode("form", { onSubmit: _withModifiers($event => (user.mfa_enabled?disableMfa():beginMfa()), ["prevent"]) }, [_createElementVNode("label", { class: "field" }, [_createTextVNode("Senha atual"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((mfa.password) = $event),
                  type: "password",
                  required: "",
                  autocomplete: "current-password"
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, mfa.password]])]), (user.mfa_enabled)
                  ? (_openBlock(), _createElementBlock("label", {
                      key: 0,
                      class: "field"
                    }, [_createTextVNode("Código do autenticador ou recuperação"), _withDirectives(_createElementVNode("input", {
                      "onUpdate:modelValue": $event => ((mfa.code) = $event),
                      required: "",
                      autocomplete: "one-time-code"
                    }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, mfa.code]])]))
                  : _createCommentVNode("", true), _createElementVNode("button", {
                  class: "btn primary",
                  disabled: busy
                }, _toDisplayString(user.mfa_enabled?'Desabilitar 2FA':'Configurar autenticador'), 9, ["disabled"])], 40, ["onSubmit"])
              ]), _createElementVNode("section", { class: "panel padded" }, [
                _createElementVNode("p", { class: "eyebrow" }, "SEU ACESSO"),
                _createElementVNode("h2", null, _toDisplayString(user.name), 1),
                _createElementVNode("p", null, _toDisplayString(user.email), 1),
                _createElementVNode("p", { class: "muted spaced" }, "Perfil: " + _toDisplayString(user.role_name), 1),
                _createElementVNode("p", { class: "muted" }, "Ao alterar senha, perfil ou 2FA, as sessões anteriores são encerradas.")
              ])]), _createElementVNode("div", { class: "panel spaced" }, [_createElementVNode("header", { class: "panel-header" }, [_createElementVNode("h2", null, "Sessões da sua conta")]), _createElementVNode("div", { class: "table-scroll" }, [_createElementVNode("table", null, [_createElementVNode("thead", null, [_createElementVNode("tr", null, [
                _createElementVNode("th", null, "Origem"),
                _createElementVNode("th", null, "Última atividade"),
                _createElementVNode("th", null, "Situação"),
                _createElementVNode("th")
              ])]), _createElementVNode("tbody", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(sessions, (s) => {
                return (_openBlock(), _createElementBlock("tr", { key: s.id }, [
                  _createElementVNode("td", null, [_createTextVNode(_toDisplayString(s.label) + " ", 1), (s.current)
                    ? (_openBlock(), _createElementBlock("span", {
                        key: 0,
                        class: "badge"
                      }, "Esta sessão"))
                    : _createCommentVNode("", true)]),
                  _createElementVNode("td", null, _toDisplayString(date(s.seen)), 1),
                  _createElementVNode("td", null, _toDisplayString(s.revoked?'Revogada':'Ativa'), 1),
                  _createElementVNode("td", null, [(!s.revoked)
                    ? (_openBlock(), _createElementBlock("button", {
                        key: 0,
                        class: "link-button",
                        onClick: $event => (revokeSession(s))
                      }, "Encerrar", 8, ["onClick"]))
                    : _createCommentVNode("", true)])
                ]))
              }), 128))])])])])], 512), [[_vShow, page==='security']]),
              _withDirectives(_createElementVNode("section", { class: "panel" }, [_createElementVNode("header", { class: "panel-header" }, [_createElementVNode("h2", null, "Histórico administrativo")]), _createVNode(_component_data_table, {
                rows: audit,
                columns: {id:'Evento',created:'Data',actor:'Usuário',action:'Ação',target:'Registro',details:'Detalhes'}
              }, null, 8, ["rows", "columns"]), _createElementVNode("div", { class: "padded" }, [_createElementVNode("button", {
                class: "btn secondary",
                onClick: olderAudit,
                disabled: !audit.length||busy
              }, "Carregar eventos anteriores", 8, ["onClick", "disabled"])])], 512), [[_vShow, page==='audit']]),
              (workspaceMounted && can('workspace.read'))
                ? _withDirectives((_openBlock(), _createElementBlock("section", {
                    key: 3,
                    class: "work-frame panel"
                  }, [_createElementVNode("iframe", {
                    id: "workspace-frame",
                    "data-owner": user.id,
                    src: "/workspace",
                    title: "Área de escrituração",
                    onLoad: selectWorkspace
                  }, null, 40, ["data-owner", "onLoad"])], 512)), [[_vShow, workspacePages.includes(page)]])
                : _createCommentVNode("", true),
              _createElementVNode("footer", { class: "content-footer" }, [_createElementVNode("span", null, "Escritura · Organização contábil"), _createElementVNode("span", null, _toDisplayString(version) + " · " + _toDisplayString(user.role_name), 1)])
            ], 2)])
          ])), dialog
      ? (_openBlock(), _createElementBlock("div", {
          key: 3,
          class: "modal-backdrop",
          onClick: _withModifiers(closeDialog, ["self"])
        }, [_createElementVNode("section", {
          class: "modal",
          role: "dialog",
          "aria-modal": "true",
          "aria-label": dialogTitle
        }, [_createElementVNode("header", { class: "panel-header" }, [_createElementVNode("h2", null, _toDisplayString(dialogTitle), 1), _createElementVNode("button", {
          class: "icon-button",
          onClick: closeDialog,
          "aria-label": "Fechar"
        }, "×", 8, ["onClick"])]), _createElementVNode("div", { class: "padded" }, [
          error
            ? (_openBlock(), _createElementBlock("div", {
                key: 0,
                class: "alert error"
              }, _toDisplayString(error), 1))
            : _createCommentVNode("", true),
          (dialog==='user')
            ? (_openBlock(), _createElementBlock("form", {
                key: 1,
                onSubmit: _withModifiers(saveUser, ["prevent"]),
                class: "form-grid"
              }, [
                _createElementVNode("label", { class: "field" }, [_createTextVNode("Nome"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((userForm.name) = $event),
                  required: ""
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, userForm.name]])]),
                _createElementVNode("label", { class: "field" }, [_createTextVNode("E-mail"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((userForm.email) = $event),
                  type: "email",
                  required: ""
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, userForm.email]])]),
                _createElementVNode("label", { class: "field" }, [_createTextVNode("Perfil"), _withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((userForm.role) = $event) }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(roles, (r) => {
                  return (_openBlock(), _createElementBlock("option", {
                    key: r.id,
                    value: r.id
                  }, _toDisplayString(r.name), 9, ["value"]))
                }), 128))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, userForm.role]])]),
                _createElementVNode("label", { class: "field" }, [_createTextVNode(_toDisplayString(userForm.id?'Nova senha (opcional)':'Senha inicial'), 1), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((userForm.password) = $event),
                  type: "password",
                  required: !userForm.id,
                  minlength: "12",
                  autocomplete: "new-password"
                }, null, 8, ["onUpdate:modelValue", "required"]), [[_vModelText, userForm.password]])]),
                _createElementVNode("label", { class: "field checkbox-field" }, [_withDirectives(_createElementVNode("input", {
                  type: "checkbox",
                  "onUpdate:modelValue": $event => ((userForm.active) = $event)
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, userForm.active]]), _createTextVNode("Conta ativa")]),
                (userForm.role!=='admin')
                  ? (_openBlock(), _createElementBlock("fieldset", {
                      key: 0,
                      class: "wide"
                    }, [_createElementVNode("legend", null, "Empresas autorizadas"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(dashboard.companies, (c) => {
                      return (_openBlock(), _createElementBlock("label", {
                        key: c.id,
                        class: "field checkbox-field"
                      }, [_withDirectives(_createElementVNode("input", {
                        type: "checkbox",
                        value: String(c.id),
                        "onUpdate:modelValue": $event => ((userForm.companies) = $event)
                      }, null, 8, ["value", "onUpdate:modelValue"]), [[_vModelCheckbox, userForm.companies]]), _createTextVNode(_toDisplayString(c.name), 1)]))
                    }), 128)), (!dashboard.companies.length)
                      ? (_openBlock(), _createElementBlock("p", {
                          key: 0,
                          class: "muted"
                        }, "Cadastre uma empresa antes de conceder acesso."))
                      : _createCommentVNode("", true)]))
                  : _createCommentVNode("", true),
                _createElementVNode("button", {
                  class: "btn primary wide",
                  disabled: busy
                }, "Salvar usuário", 8, ["disabled"])
              ], 40, ["onSubmit"]))
            : _createCommentVNode("", true),
          (dialog==='role')
            ? (_openBlock(), _createElementBlock("form", {
                key: 2,
                onSubmit: _withModifiers(saveRole, ["prevent"])
              }, [_createElementVNode("label", { class: "field" }, [_createTextVNode("Nome do perfil"), _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": $event => ((roleForm.name) = $event),
                required: ""
              }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, roleForm.name]])]), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(permissions, (label, key) => {
                return (_openBlock(), _createElementBlock("label", {
                  key: key,
                  class: "field checkbox-field"
                }, [_withDirectives(_createElementVNode("input", {
                  type: "checkbox",
                  value: key,
                  "onUpdate:modelValue": $event => ((roleForm.permissions) = $event)
                }, null, 8, ["value", "onUpdate:modelValue"]), [[_vModelCheckbox, roleForm.permissions]]), _createTextVNode(_toDisplayString(label), 1)]))
              }), 128)), _createElementVNode("button", {
                class: "btn primary",
                disabled: busy
              }, "Salvar perfil", 8, ["disabled"])], 40, ["onSubmit"]))
            : _createCommentVNode("", true),
          (dialog==='mfa')
            ? (_openBlock(), _createElementBlock("form", {
                key: 3,
                onSubmit: _withModifiers(confirmMfa, ["prevent"])
              }, [
                _createElementVNode("p", null, "Adicione uma conta no seu autenticador usando esta chave:"),
                _createElementVNode("code", { class: "secret" }, _toDisplayString(mfa.secret), 1),
                _createElementVNode("p", { class: "muted small" }, "Aplicativo: Escritura · TOTP · 6 dígitos · 30 segundos"),
                _createElementVNode("label", { class: "field" }, [_createTextVNode("Código gerado"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((mfa.code) = $event),
                  required: "",
                  autocomplete: "one-time-code",
                  inputmode: "numeric",
                  maxlength: "6"
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, mfa.code]])]),
                _createElementVNode("button", {
                  class: "btn primary",
                  disabled: busy
                }, "Confirmar ativação", 8, ["disabled"])
              ], 40, ["onSubmit"]))
            : _createCommentVNode("", true),
          (dialog==='recovery')
            ? (_openBlock(), _createElementBlock("div", { key: 4 }, [_createElementVNode("p", null, "Guarde estes códigos em local seguro. Cada código pode ser usado uma única vez. Eles não serão exibidos novamente."), _createElementVNode("pre", { class: "secret" }, _toDisplayString(recoveryCodes.join('\n')), 1), _createElementVNode("button", {
                class: "btn primary",
                onClick: closeDialog
              }, "Guardei os códigos · entrar novamente", 8, ["onClick"])]))
            : _createCommentVNode("", true)
        ])], 8, ["aria-label"])], 8, ["onClick"]))
      : _createCommentVNode("", true)], 8, ["aria-busy"]))
  }
};
