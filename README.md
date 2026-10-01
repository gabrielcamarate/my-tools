# my-tools

[![Validate](https://github.com/gabrielcamarate/my-tools/actions/workflows/validate.yml/badge.svg)](https://github.com/gabrielcamarate/my-tools/actions/workflows/validate.yml)

Gestor de ferramentas oficiais para Codex e Claude: origem, SHA aceito, instalação, atualização e recuperação. O agente usa os comandos e MCPs do próprio fornecedor. O [my-skills](https://github.com/gabrielcamarate/my-skills) orienta quando usá-los. Não criamos nomes de operações próprios para substituir as ferramentas.

O controlador usa Python 3.11+ e biblioteca padrão; Linux é o alvo validado. Regras e autorizações continuam pertencendo ao consumidor.

## Ferramenta integrada

| Ferramenta | Interface do agente | Estado |
|---|---|---|
| [Siftr](https://github.com/Bentlybro/siftr) | CLI `siftr` e MCP oficial `siftr mcp` | Experimental; quatro ferramentas disponíveis |

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

O Siftr envia caminhos, nomes de definições e trechos ao OpenRouter/TypeSafe. Só use conteúdo autorizado para esse envio. Exclua credenciais, arquivos de ambiente, dados financeiros/de clientes e logs privados. O MCP oficial não impõe allowlist de projeto por projeto. Caminhos e globs precisam respeitar a autorização da tarefa. `focused_read` e `filter_output` também exigem arquivos autorizados.

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
