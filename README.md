# my-tools

[![Validate](https://github.com/gabrielcamarate/my-tools/actions/workflows/validate.yml/badge.svg)](https://github.com/gabrielcamarate/my-tools/actions/workflows/validate.yml)

Gestor de ferramentas oficiais para Codex e Claude: origem, SHA aceito, instalação, atualização e recuperação. O agente usa os comandos e MCPs do próprio fornecedor. O [my-skills](https://github.com/gabrielcamarate/my-skills) orienta quando usá-los. Não criamos nomes de operações próprios para substituir as ferramentas.

O controlador usa Python 3.11+ e biblioteca padrão; Linux é o alvo validado. Regras e autorizações continuam pertencendo ao consumidor.

## Ferramentas integradas

| Ferramenta | Interface do agente | Estado |
|---|---|---|
| [Siftr](https://github.com/Bentlybro/siftr) | CLI `siftr` e MCP oficial `siftr mcp` | Experimental; quatro ferramentas disponíveis |
| [Jev Pruner](https://github.com/tamaratran/jev-pruner) | Plugin/skill oficial Codex e wrapper upstream | Pendente: wrapper não suporta OpenRouter; desabilitado no consumidor |

O MCP oferece `semantic_search`, `focused_read`, `pick_relevant` e `filter_output` (experimental). Fonte upstream intacta; não há proxy ou tradução dos nomes/parâmetros.

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

## Jev Pruner: compatibilidade pendente

O consumidor definiu OpenRouter como provedor único. A revisão aceita do Pruner usa diretamente a API TypeSafe, não aceita `OPENROUTER_API_KEY` pelo wrapper e tem formato de requisição diferente. Está desabilitado nesse workflow. Os comandos abaixo documentam a interface upstream para referência, não são instrução para ativá-lo com uma chave OpenRouter. Não renomeie a credencial nem crie proxy para fingir compatibilidade oficial.


Node.js 18+, npm e Codex CLI com `plugin` são necessários. Validação local: Codex 0.159.2.

```bash
my-tools install jev-pruner
my-tools integrate jev-pruner           # prévia
my-tools integrate jev-pruner --apply   # plugin oficial, compilado e com SHA aceito
my-tools doctor
```

Instalação usa Git fixado, `npm ci` com lock e sem scripts de instalação, e `npm run build` upstream. A fonte e os artefatos são verificados por hash; testes e typecheck upstream são executados sem chave nem conversa real. O plugin mantém seus arquivos originais, incluindo a skill `jev-pruner`. Não é um MCP e não usa `my-tools` para executar comandos.

Cadastre uma chave **TypeSafe** no mecanismo de ambiente/segredos do cliente para disponibilizar `TYPESAFE_API_KEY`. A credencial OpenRouter do Siftr não é intercambiável por suposição. Não cole chaves no chat, argumentos ou Git. Inicie uma sessão nova e revise o hook `jev-pruner` em `/hooks`, conforme a documentação upstream. Não elevamos sandbox, acesso à rede ou limites de saída globalmente.

Exemplo na conversa:

```text
$jev-pruner Execute o comando de testes autorizado pelo wrapper e informe o resultado.
```

A skill oficial chama `node <plugin-root>/dist/codex/run.js -- <comando>`. Só stdout acima de 10.000 tokens **estimados** é elegível; comandos não envolvidos pelo wrapper passam normalmente. Erros, documentos/código reconhecidos e formatos protegidos podem passar completos. Ausência de chave, histórico ou acesso ao provedor preserva a saída original. Só os marcadores de omissão comprovam poda.

**Dados enviados:** histórico de mensagens e entradas/resultados de ferramentas da sessão, além da saída elegível, são enviados ao TypeSafe. O filtro de segredos do comando atual não saneia automaticamente todo esse histórico. Ativação em conversas privadas exige autorização para esse conteúdo; use sessão dedicada com dados sintéticos/públicos para o primeiro teste. Os hooks de captura AI-Memory não controlam esse envio. Não leia transcrições privadas para montar testes.

Originais ficam em `.jev-pruner/` no cwd, com permissões privadas e `.gitignore` interno. Leia o arquivo do rodapé para recuperar detalhes, sem repetir o comando. Falhas de poda não são economia demonstrada. Sessões existentes precisam recarregar o plugin; desktop/Cloud e confiança efetiva no hook precisam de verificação própria.

O `filter_output` do Siftr lê um arquivo que já existe. Pruner envolve a execução de um comando e poda stdout antes de retornar ao agente, usando contexto da conversa. Não aplique os dois sobre a mesma saída por rotina. Veja [uso e atualização do Pruner](docs/jev-pruner.md).

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
