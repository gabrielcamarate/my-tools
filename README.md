# my-tools

[![Validate](https://github.com/gabrielcamarate/my-tools/actions/workflows/validate.yml/badge.svg)](https://github.com/gabrielcamarate/my-tools/actions/workflows/validate.yml)

Gestor de ferramentas oficiais para Codex e Claude: origem, SHA aceito, instalação, atualização e recuperação. O agente usa os comandos e MCPs do próprio fornecedor. O [my-skills](https://github.com/gabrielcamarate/my-skills) orienta quando usá-los. Não criamos nomes de operações próprios para substituir as ferramentas.

O controlador usa Python 3.11+ e biblioteca padrão; Linux é o alvo validado. Regras e autorizações continuam pertencendo ao consumidor.

## Ferramentas integradas

| Ferramenta | Interface do agente | Estado |
|---|---|---|
| [Jeval](https://github.com/rlaope/jeval) | CLI `jeval` e seis skills upstream | Experimental: avaliação offline de decisões rotuladas; sem chave, hooks ou MCP |
| [Siftr](https://github.com/Bentlybro/siftr) | CLI `siftr` e MCP oficial `siftr mcp` | Experimental; quatro ferramentas disponíveis |
| [Jev Pruner](https://github.com/tamaratran/jev-pruner) | Plugin/skill oficial Codex e wrapper upstream | Experimental: OpenRouter, engine upstream preservado e poda live verificada |
| [Fast Jev Compaction](https://github.com/tamaratran/fast-jev-compaction) | Plugin oficial Claude Code (function hooks `session.compact`) | Experimental: OpenRouter, motor upstream preservado; `/compact` sintético no motor e fallbacks verificados. Veja [docs](docs/fast-jev-compaction.md) |
| [Jev Test Filter](https://github.com/mizchi/jev-test-filter) | CLI `jev-test-filter` e skill upstream | Experimental: seleção live via OpenRouter, preservando gates finais |
| [Jev Browser](https://github.com/tontoko/jev-browser) | CLI `jev-browser`, MCP `jev-browser-mcp` e skill upstream | Experimental: Chromium isolado, OpenRouter e gravação/readback live verificados |

O MCP do Siftr oferece `semantic_search`, `focused_read`, `pick_relevant` e `filter_output` (experimental). Fonte upstream intacta; não há proxy ou tradução dos nomes/parâmetros.

## Instalar e conectar

```bash
git clone https://github.com/gabrielcamarate/my-tools.git
cd my-tools
python3 bin/my-tools setup --apply
my-tools install siftr
# Instale uv conforme https://docs.astral.sh/uv/getting-started/installation/
my-tools integrate siftr             # prévia
my-tools integrate siftr --apply     # entrypoint oficial, com SHA aceito
siftr setup                         # cadastro oficial da chave, sem eco
codex mcp add siftr -- "$HOME/.local/bin/siftr" mcp
my-tools doctor
```

`integrate` usa a operação oficial `uv tool install --python 3.12`, com a fonte local da revisão aceita, em diretório separado por SHA. Python pode ser obtido pelo uv. O executável oficial é publicado por symlink em `~/.local/bin/siftr`; comandos de terceiros são preservados. `--bin-dir` permite outro destino. O comando estável acompanha atualizações/rollback, sem mudar o registro MCP. Não coloque a chave em argumentos nem no Git.

A documentação upstream também oferece `siftr agents install [CLIENTE]`. Como esse instalador resolve o symlink para um caminho de versão fixa, prefira o registro manual acima para o Codex acompanhar a versão gerenciada. Para outro cliente, use o formato oficial e o caminho estável. A integração não altera configurações de clientes automaticamente. Reinicie/reconecte clientes já abertos depois de registrar ou trocar a versão: um processo MCP existente pode continuar usando a anterior. Links pessoais não se sincronizam para Cloud/outro computador.

Configuração manual equivalente no Codex:

```toml
[mcp_servers.siftr]
command = "/caminho/absoluto/para/siftr"
args = ["mcp"]
```

Use o caminho estável, não um caminho contendo o SHA. Caso o cliente exija confirmação, configure as ferramentas individualmente conforme a autorização do consumidor; o Codex suporta `mcp_servers.siftr.tools.<nome>.approval_mode`. Não libere ferramentas adicionais por padrão. Skills de descoberta podem orientar a escolha das ferramentas; instalação não garante seleção automática em todo pedido.

## Jev Pruner com OpenRouter

Node.js 18+, npm e Codex CLI com plugins são necessários. O My Tools instala o plugin upstream e aplica um pequeno patch autorizado de provedor: Decisions API do OpenRouter, `typesafe/jev-1.13` e `OPENROUTER_API_KEY`. O contrato tipado e o motor de poda permanecem upstream, sem tradução de chat ou comando de poda próprio.

```bash
my-tools install jev-pruner
my-tools integrate jev-pruner --apply
my-tools doctor
# Instalação anterior ao ajuste: my-tools repair jev-pruner
```

A instalação compila/verifica fonte, patch e cache. Uma mudança upstream que não aceita o patch impede ativação. No desktop, o wrapper reutiliza a chave privada do Siftr se ela não estiver no ambiente, sem duplicar credenciais. Outro ambiente precisa de credencial e rede próprias. Não inclua chave em argumentos, chat ou Git.

A skill `jev-pruner` chama `node <plugin-root>/dist/codex/run.js -- <comando>`. Exemplo de pedido: `$jev-pruner execute os testes autorizados pelo wrapper`. Quatro skills do my-skills orientam uso em resolução, ciclos de implementação, verificação e smoke. Apenas stdout elegível acima de 10.000 tokens estimados é podado; outras chamadas não são interceptadas. Stderr, falhas e exit status são preservados, e o original fica em `.jev-pruner/` para recuperação.

O provedor recebe histórico e stdout: autorização deve abranger ambos. O filtro do comando atual não saneia mensagens anteriores. Testes live usam sessão sintética dedicada. Não use para conteúdo sensível, dados estruturados, leitura integral, diffs, servidores ou TTY. Não aplique também Siftr `filter_output` ao mesmo resultado.

Uma fixture local foi reduzida de 22.710 para 2.930 tokens estimados, com diagnósticos e original preservados. Não é percentual de economia da tarefa inteira. O agente em uma sessão CLI nova também chamou o wrapper e recebeu poda real. Desktop precisa recarregar e confiar no hook; Cloud precisa instalar/configurar no próprio ambiente e disponibilizar histórico compatível. Veja [uso, evidência e requisitos Cloud](docs/jev-pruner.md).

## Jev Test Filter com OpenRouter

Node.js 24+, pnpm e Git são necessários. A integração instala a CLI e a skill completas do upstream, na revisão aceita, com um patch exclusivo de provedor. Usa a mesma chave OpenRouter do processo ou configuração pessoal privada do Siftr.

```bash
my-tools install jev-test-filter
my-tools integrate jev-test-filter --apply
# No projeto, para mudanças locais rastreadas contra HEAD:
jev-test-filter --format node --exec -- node --test
# Para uma base Git confirmada, adapte ao runner do projeto:
jev-test-filter --base origin/main --exec -- vitest run
```

A skill `jev-test-filter` orienta os argumentos originais. Três skills do my-skills remetem a ela em implementação, iteração e planejamento de verificação. A ferramenta seleciona testes pelo diff, não poda logs. Use quando a suíte é lenta e preserve todos os gates finais. Em uma fixture sintética, selecionou 3/20 testes e reteve as três regressões esperadas. A execução lenta simulada caiu de 2,13 s para 0,95 s; a rápida aumentou de 0,16 s para 0,85 s. Não é economia de tokens Codex medida.

`integrate` publica o executável compilado por symlink em `~/.local/bin/jev-test-filter` e a skill com referências em `~/.agents/skills/jev-test-filter`. Updates e rollback acompanham ambos, preservando instalações externas. Não requer MCP, hook nem histórico de sessão. Cloud precisa preparar esses links, runtime, credencial durante a tarefa e rede no próprio ambiente. Veja [uso, validação e Cloud](docs/jev-test-filter.md).

## Uso nativo

```bash
siftr search "onde o cancelamento é processado?" . --glob 'src/*.ts' --json --stats
siftr read src/billing.py "onde calculamos o reembolso?" --json
git ls-files 'tests/*.py' | siftr pick "testar o reembolso" --json
siftr filter "qual falha aconteceu?" /caminho/saida-saneada.log --json
```

Os caminhos são ilustrativos. Pelo MCP, o agente chama as mesmas operações oficiais com os nomes da tabela abaixo. Leia implementação/chamadores; resultados são sugestões e podem omitir evidência. Para símbolos exatos, `rg` normalmente é mais apropriado.

| Ferramenta MCP | Uso |
|---|---|
| `semantic_search` | Comportamento sem localização confirmada |
| `focused_read` | Parte relevante de arquivo grande |
| `pick_relevant` | Priorizar lista de testes/arquivos, preservando gates |
| `filter_output` | Saída existente, saneada e autorizada; experimental |

## Dados e credenciais

O Siftr envia caminhos, nomes de definições e trechos ao OpenRouter/TypeSafe. Só use conteúdo autorizado para esse envio. Exclua credenciais, arquivos de ambiente, dados financeiros/de clientes e logs privados. O MCP oficial não impõe allowlist por projeto. Caminhos e globs precisam respeitar a autorização da tarefa. `focused_read` e `filter_output` também exigem arquivos autorizados.

`siftr setup` grava a chave na configuração pessoal do próprio Siftr. A fonte upstream carrega variáveis do processo, `.env` do cwd/pais e configuração pessoal; isso é comportamento oficial, sem patch nosso. O MCP precisa receber a chave pelo mecanismo oficial. A chave fica fora do Git, em armazenamento pessoal; não é um cofre criptografado.

## Atualização e recuperação

```bash
my-tools outdated --all
my-tools update --all
my-tools update siftr --accept SHA_COMPLETO_REVISADO
my-tools rollback siftr
my-tools doctor
```

Candidato novo permanece `review_required` até aceitação explícita, salvo revisão aprovada no catálogo. Testes offline upstream e integridade são verificados antes de ativar. Se a ferramenta já tiver integração nativa, a atualização prepara também o entrypoint oficial e confere as quatro ferramentas MCP antes de alternar o symlink. Falha antes da troca preserva o comando ativo; falha de persistência tenta restaurar a versão anterior. Uma interrupção de máquina pode exigir reconciliação; `doctor` detecta divergência entre versão gerenciada e comando nativo. `integrate --apply` reconcilia com a revisão aceita. Não há transação global entre ferramentas.

Para plugins já integrados, atualização/rollback também troca a fonte do marketplace e reinstala o cache oficial do Codex; o SHA é conferido pelos arquivos, não apenas pela versão declarada. Plugins desabilitados e instalações de terceiros são preservados; uma reinstalação automática é recusada nesses casos.

Mantenha runtimes anteriores para rollback. Não use `uv tool upgrade` fora do gestor para esta instalação: isso perde o vínculo com o SHA aceito. Reinicie processos MCP depois da troca. Compatibilidade offline não comprova acurácia nem ganho de produtividade; avalie qualidade antes de aceitar versões. Leitura/revisão de mudanças upstream continua necessária. Checks executam código de terceiros e não constituem sandbox de sistema contra código hostil.

## Avaliação

```bash
my-tools compare benchmarks/examples/baseline.json benchmarks/examples/candidate.json
python3 -m unittest discover -s tests -v
python3 scripts/check_public.py
```

Exemplos são sintéticos. Resultados reais ficam no registro autorizado do consumidor. Compare tarefas equivalentes, tempo total, qualidade e tokens reais; disponibilidade não prova economia de cota ChatGPT.

Veja [arquitetura](docs/architecture.md), [MCP e skills](docs/skills.md), [atualizações](docs/updates.md), [protocolo](benchmarks/protocols/search.md) e [proveniência](NOTICE.md).

Licença MIT do controlador; ferramentas externas preservam suas licenças.

## Jev Browser com OpenRouter

[Guia de instalação, comandos, Cloud e testes](docs/jev-browser.md). Node.js 24+ recomendado (upstream: 22.15+), npm e Chromium/Playwright são necessários.

```bash
my-tools install jev-browser
my-tools integrate jev-browser --apply
# Obtenha SOURCE a partir do link oficial já integrado:
SOURCE="$(dirname "$(dirname "$(readlink -f "$(command -v jev-browser)")")")"
node "$SOURCE/node_modules/playwright-core/cli.js" install --with-deps chromium
codex mcp add jev-playwright -- "$HOME/.local/bin/jev-browser-mcp"
my-tools doctor
```

A CLI e o MCP são os entrypoints upstream, publicados por links estáveis que acompanham update/rollback. O patch muda somente provedor e orientação/testes associados. A skill upstream completa fica vinculada em `~/.agents/skills/jev-browser-playwright`, fora do my-skills. Esse nome e o registro MCP `jev-playwright` evitam colisão com outro Jev Browser Control usado no Chrome pessoal; comandos e ferramentas MCP upstream não são renomeados. Reabra/reconecte clientes existentes após o registro.

Operações nativas não exigem inferência. Metas semânticas usam `OPENROUTER_API_KEY`, com o mesmo fallback privado do Siftr; não copie a chave para cada projeto. Use apenas páginas/dados autorizados. A ferramenta não assume o navegador pessoal nem substitui revisão visual, gates ou confirmação de ações.

## Descoberta das skills no Claude

`my-tools integrate jev-test-filter --apply` e `my-tools integrate jev-browser --apply`
também criam links individuais em `~/.claude/skills` para os links estáveis de
`~/.agents/skills`. A fonte upstream continua única e updates/rollback acompanham
ambos os clientes. Não há cópia de skills nem MCP registrado automaticamente no Claude.
Reaplique integrate nas instalações antigas: o registro antigo é compatível, mas
`doctor` informa `claude_skill_status: not_registered` até essa reconciliação.
Conflitos externos abortam antes de trocar qualquer link; falhas compensam a troca.
Após configurar, uma nova sessão pode ser necessária para atualizar o catálogo.

## Jeval: medir a confiabilidade das decisões

```bash
my-tools install jeval
my-tools integrate jeval --apply
jeval demo --out-dir /tmp/jeval-demo
# Para registros autorizados com rótulos:
jeval ingest decisions.jsonl --root /caminho/avaliacao
jeval report --root /caminho/avaliacao
```

Jeval 0.2.0 é uma CLI offline, sem alteração upstream nem chave necessária. Python 3.12/uv instalam o pacote oficial `jeval-cli` a partir da fonte aceita e do `uv.lock`, em runtime separado por SHA. Não use `pip install jeval`: esse nome pertence a outro pacote. Seis skills oficiais ficam vinculadas à fonte no armazenamento My Tools, com links Codex/Claude. Update e rollback acompanham CLI e skills.

O teste real usou decisões Jev via OpenRouter e rótulos sintéticos. A avaliação distinguiu 16 acertos de uma amostra insuficiente; um controle com 40 erros em 200 decisões revelou excesso de confiança. O benefício é verificar qualidade antes de automatizar, sem economia direta de tokens comprovada. Não instrumentamos projetos nem criamos benchmarks automáticos. Cloud precisa instalar runtime/links e receber instruções, mas não depende de MCP ou segredo para avaliar arquivos. Veja [uso, testes e limites](docs/jeval.md).

## Dez ferramentas adicionais

Versões fixadas e interface upstream, com a chave OpenRouter compartilhada. [Comandos, skills, testes, hooks e requisitos Cloud](docs/reviewed-tools.md).

| Ferramenta | Função |
|---|---|
| [jev-calibrate](https://github.com/smkrv/jev-calibrate) | Avalia perguntas e limiares com exemplos rotulados |
| [jev-axi](https://github.com/shiftynick/jev-axi) | Classifica e ordena decisões em lote |
| [jev-recipes](https://github.com/agencyenterprise/jev-recipes) | 248 decisões tipadas para automações e aplicações |
| [tocsin](https://github.com/TPAteeq/tocsin) | Agrupa e prioriza padrões de logs |
| [docjev](https://github.com/jerryjliu/docjev) | Classifica documentos e separa páginas |
| [jev-spec](https://github.com/nozomi-koborinai/jev-spec) | Compara código com requisitos Markdown |
| [jev-oas-sentinel](https://github.com/ShuhanSun/jev-oas-sentinel) | Detecta riscos de incompatibilidade OpenAPI |
| [hunch](https://github.com/Kelbie/hunch) | Busca comportamento e revisa diffs contra regras |
| [snifftest](https://github.com/DanRWilloughby/snifftest) | Verifica texto contra regras de estilo |
| [semdecide](https://github.com/sharziki/semdecide) | Classifica e filtra texto ou JSONL |

## Fase experimental de uso: 03/10/2026

As skills pessoais do [my-skills](https://github.com/gabrielcamarate/my-skills/blob/main/docs/tool-routing.md)
agora exigem executar a ferramenta oficial ao ocorrer um gatilho compatível, com
chamada/resultado ou dispensa concreta e fallback registrados na tarefa. Ler a skill
não conta como uso. É uma regra de instruções para medir adoção, não interceptação
global ou prova de economia. Gates finais, autorização de dados e recuperação
continuam obrigatórios. Não foram alterados instalação, hooks ou credencial.

### Adoção local: correções e validação

Siftr aceita filtros fnmatch, sem `{ts,tsx}`. Use raiz estreita ou filtros repetidos
`-g "*.ts" -g "*.tsx"`. O perfil pessoal do Pruner permanece fora do Git; ele precisa
autorizar o histórico inteiro elegível. Smokes isolados usam Jev Browser oficial;
suítes Playwright existentes continuam gates independentes. Ver
[aceitação local](docs/local-adoption.md). Pruner reduz saída de comandos, não
substitui a compactação de conversa do Codex.

## Laboratório opcional: compactação Codex com Jev

O [laboratório isolado](experiments/codex-jev/README.md) avalia um fork do motor
Codex, com origem/SHA fixados, patch OpenRouter e comparação do mesmo binário
com Jev ligado/desligado. Não substitui o `codex` instalado, não registra hooks
e não ativa compactação nas conversas normais. Não faz parte de `install/update
--all`: sua compatibilidade é a do motor, não a de uma CLI/plugin comum.
Resultados do helper e do motor têm evidências separadas; o backend sintético
não comprova latência nem qualidade real do ChatGPT. A skill `gabriel-reflect`
aponta para a avaliação somente quando esse experimento for autorizado.

A [extensão gerenciada para CLI e Desktop](experiments/codex-jev/MANAGED.md)
acompanha separadamente os pacotes instalados. Seus launchers opt-in e o hook
pessoal de atualização do Omarchy são uma instalação explícita, fora do ciclo
`install/update --all`. O app principal é preservado. Novas versões passam em
gates offline antes de ativar Jev; falhas deixam a compactação oficial disponível.
