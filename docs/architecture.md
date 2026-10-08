# Arquitetura

```text
my-tools: catálogo/SHA → fonte verificada → uv tool install → entrypoint oficial
cliente MCP → siftr mcp → handlers oficiais → provedor → resultado ao agente
```

O gestor não participa das chamadas do agente. Não há proxy, cadastro de chave próprio, perfis ou configuração por projeto. O catálogo registra origem, licença, SHA aceito e instalador. O my-skills orienta a escolha das ferramentas oficiais; plugins podem fornecer suas próprias skills upstream.

`state.json` registra versões aceitas, ativa e anterior. `tools/<nome>/<sha>/` contém fonte Git verificada, hashes e um Python isolado usado somente para checagens offline. Siftr não altera operações ou carregamento de credenciais upstream. Pruner aplica o patch de provedor documentado, com hash próprio além do SHA upstream. `native/<nome>/<sha>/` contém a instalação oficial gerada pelo uv.

`native.json` registra comando estável e SHA instalado. Atualização/rollback de ferramenta integrada verifica o contrato MCP antes de trocar o symlink. Processos existentes precisam reconectar. Persistência usa replace atômico e lock POSIX; restauração entre arquivos é compensatória. `doctor` detecta divergência; `integrate --apply` reconcilia a revisão aceita.

`plugins.json` registra a fonte aceita do plugin Codex. Para Jev Pruner, a fonte é compilada com npm e vinculada em `plugins/jev-pruner`. A integração registra o marketplace local e o plugin oficial; o cache é reinstalado a cada troca de SHA. O gestor confere o cache e restaura a versão anterior em falhas recuperáveis. Não registra MCP ou inventa chamadas para o Pruner.

`claude-plugins.json` registra a fonte aceita do Fast Jev Compaction. A integração usa os comandos oficiais `claude plugin marketplace add`/`install` sobre a fonte gerenciada, confere o cache instalado e só acrescenta a flag de function hooks em `~/.claude/settings.json`, preservando hooks existentes.

## Acrescentar uma ferramenta

1. Definir tarefa, baseline e critério de aceite.
2. Registrar origem HTTPS pública, licença e SHA revisado.
3. Implementar somente o ciclo de instalação/verificação em `installers.py` e registrar a interface oficial em `native.py`.
4. Testar candidato inválido, preservação do ativo, falha de persistência e rollback.
5. Documentar instalação oficial, envio de dados e procedimento de avaliação.
6. Orientar uso nas skills pertinentes e medir tarefas equivalentes.

Não crie aliases de operações. O catálogo inclui somente ferramentas integradas. Instalação não concede autorização de envio de dados, merge ou deploy.

## Limites

Instalação e inferência exigem rede; inferência exige credencial oficial. Venv e checagens offline não são sandbox de segurança contra código hostil. Hashes detectam mudanças acidentais; não protegem de um invasor que controla a conta e os registros. Versões oficiais anteriores são mantidas para rollback. Aceitação técnica não comprova qualidade de decisões nem economia de tokens.

Para Pruner, repair recompila o mesmo SHA em staging e restaura fonte/cache em falha recuperável. Atualização verifica aplicação do patch antes da troca; não tenta traduzir protocolos ou resolver conflitos automaticamente. A configuração OpenRouter preserva a API de decisões tipadas e o motor original.

## CLIs com skills upstream

`commands.json` registra os destinos e SHA da CLI/skill do Jev Test Filter. A fonte é instalada com `pnpm install --frozen-lockfile --ignore-scripts`, compilada e verificada; o patch de OpenRouter só muda transporte, carregamento da credencial e orientação do provedor. `commands.py` publica o arquivo upstream `dist/cli.js` diretamente e a pasta completa da skill. Não há wrapper de seleção criado pelo gestor.

Atualização/rollback verificam o candidato antes de trocar os dois links. Preflight protege destinos externos; falhas de troca/persistência restauram os links anteriores. `doctor` confere hashes de fonte/compilação e os destinos, além dos testes offline upstream. Não constitui sandbox nem comprova integridade de todo runtime/dependência instalada.

## Browser SDK / CLI / MCP

O instalador `jev-browser-source-v1` fixa fonte/licença/SHA, aplica patch de transporte com allowlist de arquivos e compila com npm ci (lockfile, scripts de instalação desativados). Verifica contratos, hashes de fonte/dist, casos de provedor e descoberta MCP sem iniciar browser. A suíte completa e testes live são avaliações explícitas, não repetidos automaticamente por doctor.

`commands.json` também registra Jev Browser: CLI, MCP e skill completa. Os três links trocam juntos após preflight; falhas de link/registro/estado compensam a versão anterior, preservando destinos externos. O cliente registra o entrypoint estável com o nome `jev-playwright`; não há proxy nem wrapper operacional. A skill é identificada como `jev-browser-playwright` para evitar colisão de catálogo com Jev Browser Control. Sua referência relativa aponta para os documentos preservados no checkout upstream.

Browser Chromium e dependências de sistema têm ciclo separado e são preparados pelo instalador oficial Playwright no ambiente. A gestão de SHA não remove o cache compartilhado de browsers. Não transporta configuração pessoal, cookies ou credenciais para projetos/Cloud. O patch OpenRouter preserva state/questions, validação de escolha, timeout/retry e respostas tipadas; adapta só URL/autenticação/modelo e carrega a credencial compartilhada somente no destino OpenRouter HTTPS.

## Descoberta das skills no Claude

`my-tools integrate jev-test-filter --apply` e `my-tools integrate jev-browser --apply`
também criam links individuais em `~/.claude/skills` para os links estáveis de
`~/.agents/skills`. A fonte upstream continua única e updates/rollback acompanham
ambos os clientes. Não há cópia de skills nem MCP registrado automaticamente no Claude.
Reaplique integrate nas instalações antigas: o registro antigo é compatível, mas
`doctor` informa `claude_skill_status: not_registered` até essa reconciliação.
Conflitos externos abortam antes de trocar qualquer link; falhas compensam a troca.
Após configurar, uma nova sessão pode ser necessária para atualizar o catálogo.

## Jeval

`jeval-source-v1` verifica SHA, contrato e hashes da fonte intacta; smoke gera um relatório demo num runtime temporário. `integrate` usa `uv sync --frozen --no-dev --no-editable --python 3.12` com `UV_PROJECT_ENVIRONMENT` no destino final por SHA, preservando os shebangs. Registra hashes do runtime e dependências, excluindo bytecode mutável. `jeval.json` guarda destinos e revisão; treze links publicam uma CLI, seis skills e seis aliases Claude. Conflitos externos são recusados antes de construir/trocar; falhas de links/persistência compensam a troca. Atualização aceita e rollback usam o mesmo mecanismo, sem envolver chamadas do agente. O comando avalia arquivos offline; não fornece MCP/hooks nem instrumentação automática.

## Interfaces revisadas

`reviewed-source-v1` compartilha somente lifecycle. Cada ferramenta fixa manifesto, comandos, skills e allowlist do patch; alteração de dependências exige revisão. CLI/skills acompanham update e rollback com preflight de ownership e compensação. Python é instalado no caminho final, sem mover shebangs. Fonte, dist e runtime Python têm hashes; node_modules não é integralmente coberto. Reparo preserva fonte/runtime anteriores em falhas. Consulte docs/reviewed-tools.md.
