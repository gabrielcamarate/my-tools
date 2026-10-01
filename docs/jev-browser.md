# Jev Browser: sessões isoladas com OpenRouter

Origem: [tontoko/jev-browser](https://github.com/tontoko/jev-browser), Apache-2.0,
versão 0.14.2, SHA `94f8814fd9af914749c00b8b91192d307ffbb35d`.
O código completo é obtido do upstream durante instalação; não é vendorizado.

## O que faz e quando usar

SDK Playwright, CLI persistente e MCP do mesmo engine. Executa ações nativas,
escolhe alvos por significado, preenche formulários, extrai dados, executa metas
completas e verifica resultados. Use em E2E e fluxos autorizados de aplicações.
Seletores conhecidos e operações exatas podem dispensar inferência. Para UX
visual, é necessário observar imagens; o DOM sozinho não comprova aparência.

A skill upstream completa permanece na instalação e é vinculada como
`jev-browser-playwright`. O registro MCP sugerido é `jev-playwright`, evitando
colisão com outro Jev Browser Control usado no Chrome pessoal. Os comandos
`jev-browser`, `jev-browser-mcp` e ferramentas `browser_*` permanecem oficiais.
O my-skills contém somente instruções de seleção nas skills de navegador,
planejamento de verificação e smoke de release.

## Instalação

```bash
my-tools install jev-browser
my-tools integrate jev-browser --apply
SOURCE="$(dirname "$(dirname "$(readlink -f "$(command -v jev-browser)")")")"
node "$SOURCE/node_modules/playwright-core/cli.js" install --with-deps chromium
codex mcp add jev-playwright -- "$HOME/.local/bin/jev-browser-mcp"
my-tools doctor
```

`--with-deps` usa a instalação oficial de bibliotecas do sistema e pode exigir
privilégios no ambiente. Se já disponíveis, `install chromium` basta. Nenhum
comando recebe a chave por argumento. Reabra/reconecte o cliente após registrar
MCP/skill ou atualizar a revisão. Operações que exigem aprovação seguem o
cliente: um teste não interativo precisa de aprovação limitada aos comandos
autorizados, não de liberação geral do servidor. Instalação não garante seleção automática:
a skill orienta o agente conforme a tarefa e a capacidade disponível.

## Provedor e credencial compartilhada

O patch autorizado modifica somente transporte/autenticação/modelo e
orientação/testes de provedor. Preserva o SDK TypeSafe e seu contrato de
state/questions/answers, validação de escolha/confiança, engine, MCP e CLI.
A injeção de fetch do SDK encaminha `/v1/systemone` para
[OpenRouter Decisions API](https://openrouter.ai/blog/insights/what-is-jev/):
`https://openrouter.ai/api/alpha/decisions`, modelo `typesafe/jev-1.13`.
Não usa chat completions nem inventa probabilidades.

`OPENROUTER_API_KEY` explícita tem precedência. Se ausente, lê apenas a chave
no cadastro privado pessoal `~/.config/siftr/.env` quando arquivo regular sem
permissões de grupo/outros. Variável explicitamente vazia desabilita fallback.
Não lê `.env` de projetos nem copia credenciais. A chave OpenRouter do ambiente
não é encaminhada para endpoints personalizados; redirects são recusados nesse
transporte. O cofre Cloud e o cadastro pessoal local são independentes.

## Uso oficial

```bash
jev-browser open http://127.0.0.1:3000 --session smoke
jev-browser run --session smoke --args '{"instruction":"Create a contact using the supplied values, Save and verify the new record.","values":{"name":"Synthetic Contact","email":"contact@example.invalid"}}'
# Exemplo de assert: adapte alvo/texto ao contrato real da aplicação.
jev-browser assert --session smoke --args '{"target":"h2","property":"text","expected":"Contact created"}'
jev-browser close --session smoke
```

No MCP, use `browser_goto` com URL, depois `browser_run` com `instruction` e
`values`. Confira `status`, `verification.readback`, `unobserved` e `effects`.
Use `browser_assert` para fatos exatos e `browser_close` para liberar a sessão.
Uma gravação `unknown` exige reconciliação somente leitura antes de qualquer
reenvio. Mensagem de sucesso não substitui o registro persistido quando este
for o critério. Feche apenas recursos próprios. Uploads requerem `file-root`;
não habilite evaluate/rede/armazenamento extras sem necessidade e autorização.
Não transfira perfil, cookies ou login do Chrome pessoal para essa sessão.

## Atualizar e recuperar

```bash
my-tools outdated --all
my-tools update --all
# Somente após revisar origem, patch e testes do candidato:
my-tools update jev-browser --accept SHA_COMPLETO_REVISADO
my-tools rollback jev-browser
```

Candidato ainda não aceito fica em `review_required`. Um patch incompatível não
ativa a versão. CLI/MCP/skill acompanham update/rollback por três links estáveis;
destinos externos são preservados e falhas de troca/persistência restauram os
links anteriores. Rollback requer revisão anterior aceita. Processos MCP em
execução precisam reconectar; um link novo não troca código já carregado.

## Codex Cloud com os três repositórios

É utilizável em ambiente preparado, sem depender do Chrome do computador.
Ter os repositórios do projeto, my-skills e my-tools é necessário, mas ainda
é preciso preparar:

1. Node 24+ recomendado, npm, Python 3.11+, Git, Chromium e bibliotecas Linux.
2. Instalar/integrar a ferramenta conforme acima e instalar os links de
   my-skills pelo seu procedimento oficial. Registrar MCP no cliente Cloud
   quando este suportar configuração local; caso contrário usar a CLI oficial.
3. Solicitar `OPENROUTER_API_KEY` na configuração do ambiente, com o mesmo nome
   do cofre pessoal. Apenas valores solicitados chegam à tarefa.
4. Permitir HTTPS/POST para `openrouter.ai`, os sites da tarefa e localhost.
   Instalação também precisa de GitHub, npm e hosts CDN do Playwright.
5. Se houver proxy HTTP/HTTPS, fazer Node fetch respeitá-lo: no Node 24+
   compatível, definir `NODE_USE_ENV_PROXY=1` antes do processo. Configure
   `NO_PROXY` para localhost/127.0.0.1 conforme a política do ambiente.
6. Testar e publicar/republicar o ambiente preparado; tarefas antigas mantêm
   seu próprio estado. Essa publicação é uma ação separada do push do repo.

Fontes verificadas em 01/10/2026:
[Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environments),
[Node proxy configuration](https://nodejs.org/learn/http/enterprise-network-configuration).
Cloud atual disponibiliza variáveis/segredos conforme sua configuração durante
setup e tarefas; não transportar regras de Cloud Legacy automaticamente.
Com segredo de rede, o programa recebe placeholder e o proxy substitui o valor
na requisição HTTPS autorizada; exige proxy funcionando. Variável direta é
lida pelo programa. O cofre não sincroniza arquivo privado local.

Preparação local em HOME limpo comprova portabilidade limitada. Não foi criada
nem executada uma thread Cloud, nem comprovada sua rede, cofre ou descoberta MCP.

## Verificação e avaliação explícitas

`install`/`doctor` verificam integridade, contratos, testes de provedor e descoberta
MCP sem iniciar Chromium. Não executam a suíte completa/live em cada diagnóstico.
A revisão passou pelos 650 testes upstream e 3 testes adicionais de provedor.
Os testes do controlador cobrem proteção de terceiros, rollback e falhas de
persistência dos três links. Avaliação live usa somente fixtures sintéticas:

```bash
SOURCE="$(dirname "$(dirname "$(readlink -f "$(command -v jev-browser)")")")"
# Suíte offline completa explícita (Chromium precisa estar preparado):
(cd "$SOURCE" && OPENROUTER_API_KEY='' npm test)
# Avaliação sintética live, com a credencial compartilhada disponível:
node benchmarks/run-browser.mjs "$SOURCE"
```

O benchmark compara uma única amostra de formulário de 16 campos com seletores
conhecidos a uma meta semântica do SDK. Outros casos verificam formulário
aninhado, wizard e MCP. Compara operações chamadas, tempo e uso Jev; **não mede
tokens/turnos Codex economizados**. Um script determinístico pronto pode ser
mais rápido. O ganho potencial é evitar que o agente conduza cada ação e leia
cada estado intermediário. A disponibilidade de 41 ferramentas MCP também
pode acrescentar custo de descoberta; não chamar Jev a cada clique conhecido.
Não há coleta automática de benchmarks. Resultados de tarefas reais pertencem
ao registro autorizado do projeto consumidor.
