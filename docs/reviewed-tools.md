# Dez ferramentas adicionais: 03/10/2026

Integrações experimentais, com revisão fixada em `tools.json`, CLIs oficiais e OpenRouter. O My Tools controla instalação, atualização, integridade e links; não substitui as operações por wrappers próprios.

| Ferramenta | O que faz e quando usar | Skills pessoais que orientam uso |
|---|---|---|
| Jev Calibrate | Avalia perguntas em exemplos rotulados, mede erros e ajuda escolher limiares antes de automatizar decisões. | verification-planning, loop-engineering |
| Jev Axi | Escolhe, classifica, ordena e faz triagem em lote pelo terminal. | iss-audit, loop-engineering |
| Jev Recipes | 248 decisões prontas e tipadas para automações/aplicações JS/TS; também possui CLI. | improve-codebase-architecture |
| Tocsin | Agrupa logs repetidos e avalia cada padrão para priorizar investigação. | iss-audit |
| DocJev | Classifica documentos e separa pacotes por intervalos de páginas. Não verifica fatos. | fact-check |
| Jev Spec | Compara código com requisitos Markdown e rubricas explícitas. Parecer consultivo. | pr-audit, verification-planning |
| Jev OAS Sentinel | Compara contratos OpenAPI e detecta riscos estruturais/semânticos de incompatibilidade. | pr-audit, verification-planning |
| Hunch | Busca código por comportamento e revisa diffs contra regras. Evitar repetir a busca do Siftr. | pr-audit, iss-audit |
| Sniff Test | Verifica rascunhos contra regras de estilo e julgamentos por parágrafo. Revisar cada alerta. | humanizer |
| SemDecide | Classifica, pontua e filtra texto/JSONL em scripts com critérios delimitados. | loop-engineering |

Os nomes abreviados da última coluna têm prefixo `gabriel-`. As 23 skills pessoais continuam 23. Nenhum parecer probabilístico substitui testes, revisão, autorização de merge/deploy ou aceitação operacional.

## Instalação e comandos

Node.js 22+, Git e npm/npx para as CLIs JS; Python 3.12 e uv para DocJev, Sentinel e SemDecide. Hunch/Sniff usam Bun 1.3.5 fixado via npx no build. Tocsin precisa de Rust 1.90.0 via mise (`mise install rust@1.90.0`); não alteramos versões globais. Rede e diretórios de runtime/cache graváveis são necessários.

```bash
my-tools install jev-axi
my-tools integrate jev-axi --apply
my-tools doctor
my-tools outdated --all
my-tools update --all
my-tools rollback jev-axi
my-tools repair jev-axi
```

Substitua o nome por qualquer ferramenta do lote. Update só ativa candidatos aceitos/validados; alterações de manifesto ou conflito de patch exigem revisão e preservam o ativo. Repair recompila a mesma revisão após mudança de patch, recusa fontes modificadas e restaura a anterior se falhar. Não usar auto-update upstream ou instaladores flutuantes mencionados nas skills.

Para instalar/integrar o lote inteiro, execute `python3 scripts/install_reviewed.py` dentro do checkout My Tools. Esse é também o passo repetível para o script de instalação Cloud, depois de preparar os runtimes. O script para no primeiro erro, não altera segredos e preserva interfaces externas. Reaplicar é idempotente para revisões já instaladas e íntegras.

| CLI oficial: exemplo | Pré-requisito |
|---|---|
| `jev-calibrate check --provider openrouter --dir ./calibration --json` | Perguntas e exemplos rotulados; confirmar revisão congelada em holdout. |
| `jev-axi pick "Qual equipe?" --options billing,technical --text "Cobrança duplicada" --json` | Categorias delimitadas e entrada autorizada. |
| `jev-recipes describe route` / `jev-recipes run route input.json` | JSON conforme schema; CLI instalada não adiciona a biblioteca a cada projeto. |
| `tocsin triage logs.txt --only page,ticket,log` | Logs autorizados; preservar originais e diferenças relevantes. |
| `docjev classify documento.pdf --rules rules.yaml` | Categorias explícitas; conferir fronteiras antes de exportar pacotes. |
| `jev-spec check --format json` | Configuração, requisitos Markdown e rubricas do projeto. |
| `jev-oas-sentinel compare --base base.json --head head.json --no-config` | Contratos OpenAPI antes/depois. |
| `hunch find "onde devolvemos créditos?" --provider typesafe --no-fallback` | Repositório autorizado; `typesafe` é o nome upstream da rota adaptada para OpenRouter. |
| `snifftest check draft.md --format json --yes` | Regras adequadas ao idioma; `--yes` autoriza envio somente da entrada escolhida. |
| `semdecide is "Pede reembolso?" --text "Devolva a cobrança duplicada" --json` | Critério delimitado e política para incerteza/falhas. |

Fixtures, regras e gates de projeto não são implantados automaticamente. Consulte `--help` e a skill upstream somente da ferramenta adequada.

## Chave e transporte

Usar a mesma `OPENROUTER_API_KEY`. Localmente o fallback reutiliza `~/.config/siftr/.env`, com permissões restritas; testes sem HOME não consultam o diretório real do usuário. Não copiar chave por ferramenta/projeto. No Cloud, o binding precisa estar disponível ao subprocesso.

O perfil usa `https://openrouter.ai/api/alpha/decisions` e `typesafe/jev-1.13`. Calibrate já suporta OpenRouter nativamente: sempre selecionar `--provider openrouter`. Hunch: sempre `--provider typesafe --no-fallback`. Os patches adaptam transporte, chave/modelo, ajuda e testes de provedor, preservando a lógica upstream. Respostas continuam validadas pelos contratos originais. O alias do modelo pode mudar sem mudar o código; registrar o modelo respondido.

DocJev foi instalado para PDF/OCR local. DOCX/PPTX requerem LibreOffice; OCR Cloud e baselines de outros provedores são extras upstream, fora deste perfil OpenRouter. Não criar outras chaves para ativá-los.

Benchmarks antigos não aprovam este perfil. Custos impressos podem ser estimativas upstream e não medem economia de tokens Codex.

## Skills, hooks e Cloud

Skills oficiais vinculadas à fonte no armazenamento upstream, fora do my-skills: `jev-axi`, `adopting-jev`, `jev-recipes`, `jev-spec-init`, `jev-spec-fix`, `hunch`, `snifftest`. Links individuais em `~/.agents/skills` e `~/.claude/skills` acompanham atualização/rollback. As outras cinco não fornecem SKILL.md nesta revisão.

O lote funciona por CLI; nenhum MCP foi registrado no host. Axi tem supervisão/safety opcionais, Spec/Sniff têm hooks Git opcionais. Não foram habilitados: instalar não concede supervisão de sessões ou criação de gates em todos os projetos. Desde 03/10/2026, as skills pessoais exigem chamada oficial nos gatilhos compatíveis
da fase experimental: [política de uso](https://github.com/gabrielcamarate/my-skills/blob/main/docs/tool-routing.md).
É uma obrigação nas instruções, sem interceptação global de ferramentas. Ausência de
entrada/configuração/autorização ou falha real exige dispensa/fallback concreto, sem
impedir a continuação da tarefa. Não obriga chamar todas as ferramentas em todo pedido.

Cloud: utilizável pelo shell após instalação destas revisões, runtimes/dependências, rede/proxy/CA, binding da chave e instruções carregadas. Ter os três repositórios não instala binários nem atualiza um ambiente aberto. Os ambientes publicados anteriormente precisam incluir estes novos nomes no script de instalação; não foram alterados nesta etapa. Instalação local não prova catálogo ou execução Cloud.

## Evidência e limites

As dez chamadas reais sintéticas pelo OpenRouter passaram: cobrança classificada por Axi/Recipes; duas mensagens rotuladas avaliadas por Calibrate; logs agrupados/triados por Tocsin; PDF sintético identificado como invoice por DocJev; reembolso confirmado por Spec; comparação semântica OpenAPI por Sentinel; localização de credits.py por Hunch; cinco perguntas de estilo respondidas por Sniff; predicado de reembolso verdadeiro com 0,99 por SemDecide. Veja as [saídas sanitizadas](../benchmarks/results/batch-2026-10-02/live.json).

Os checks do controlador cobrem update/rollback das dez interfaces, conflitos externos e compensação de falhas. O piloto não prova acurácia geral, ganho de tempo/tokens, confiabilidade em produção ou precisão de estilo em português. DocJev split e Hunch review requerem avaliação representativa adicional. Nenhum coletor automático, instrumentação de serviços ou envio de projetos privados foi habilitado.

Validação final: 90 testes do controlador, 7 testes do instalador de skills e 23 skills pessoais válidas. Suites upstream passaram nas dez revisões adaptadas; testes opt-in/ignorados pelo upstream foram preservados. Recipes: 6.200 testes de receitas e 177 de tooling, com dependência do exemplo vinculada à fonte revisada. Veja [revisões, patches e contagens](../benchmarks/results/batch-2026-10-02/validation.json). O piloto real pode ser repetido com `python3 benchmarks/run-reviewed.py`; ele exige a chave compartilhada e envia somente fixtures sintéticas.

## Adoção obrigatória e próxima tarefa local

O agente registra gatilho, interface/chamada, resultado ou falha e dispensa/fallback
no checkpoint existente, com resumo curto na entrega. Disponibilidade ou leitura
de skill não contam como execução. Sem baseline comparável, ganho permanece
desconhecido. Não foram criados hooks, gates ou coletores nesta mudança de instruções.

No localhost, links válidos de my-skills apontam à fonte canônica e acompanham seu
conteúdo; uma tarefa nova deve carregar as skills atualizadas. Sessões já abertas
podem manter instruções antigas. Outros computadores/Cloud precisam atualizar seu
checkout e preparar interfaces; push no GitHub não comprova atualização do runtime.
