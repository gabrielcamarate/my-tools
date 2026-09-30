# my-tools

[![Validate](https://github.com/gabrielcamarate/my-tools/actions/workflows/validate.yml/badge.svg)](https://github.com/gabrielcamarate/my-tools/actions/workflows/validate.yml)

Programas reutilizáveis para o workflow de Codex e Claude. Uma fonte central,
versões fixadas e ativação explícita por projeto. O controlador usa Python 3.11+
e biblioteca padrão; instalação exige Git e suporte a `venv`. Linux é o alvo
validado. Windows ainda não é suportado (locks POSIX e layout de runtime).

O [my-skills](https://github.com/gabrielcamarate/my-skills) centraliza procedimentos.
Este pacote centraliza suas ferramentas executáveis. Regras e autorizações
continuam pertencendo ao projeto consumidor.

## Primeira capacidade

| Capacidade | Ferramenta | Estado |
|---|---|---|
| Busca semântica de código | [Siftr](https://github.com/Bentlybro/siftr) | Experimental; compatibilidade offline verificada; adoção depende da avaliação no consumidor |

O Siftr envia caminhos, nomes de definições e trechos elegíveis ao provedor
OpenRouter ou TypeSafe. Ele pode omitir evidência. Confira os arquivos retornados
e use busca lexical/leitura completa quando necessário. Não há fallback lexical
automático neste adaptador. Termos exatos normalmente favorecem `rg`.

## Preparação pessoal

```bash
git clone https://github.com/gabrielcamarate/my-tools.git
cd my-tools
python3 -m unittest discover -s tests -v
python3 scripts/check_public.py
python3 bin/my-tools setup             # mostra o plano
python3 bin/my-tools setup --apply     # link pessoal em ~/.local/bin
my-tools install siftr
my-tools doctor
```

`~/.local/bin` precisa estar no PATH. Caso não esteja, use `python3 bin/my-tools`
diretamente ou configure seu shell. O setup preserva comandos de terceiros.
Os programas upstream ficam fora do Git, em `~/.local/share/my-tools`.
`MY_TOOLS_HOME` permite outro armazenamento; `setup --bin-dir` permite testar
o launcher em um diretório isolado. Nenhum MCP/hook é instalado implicitamente.

Credenciais podem vir do ambiente (`OPENROUTER_API_KEY` ou `TYPESAFE_API_KEY`)
ou de um cadastro pessoal persistente, fora do checkout:

```bash
my-tools auth set --provider openrouter   # ou typesafe; solicita chave oculta
my-tools doctor
my-tools auth remove --provider openrouter
```

O cadastro fica em `~/.local/share/my-tools/credentials.json` (ou MY_TOOLS_HOME),
com permissão 600 e propriedade da conta atual. É arquivo local em texto claro,
não um cofre criptografado. A chave não é argumento de comando nem saída de log.
Variáveis explícitas do processo prevalecem sobre o cadastro. O adaptador
desabilita dotenv upstream e não lê credenciais dos projetos.
`doctor` informa presença e origem, nunca o valor. Instalação e
verificações offline funcionam sem credenciais. Inferência requer acesso válido
ao provedor. O cadastro local permite ao launcher reutilizar a chave depois de
fechar o terminal; ele não configura credenciais em outros computadores/Cloud.

## Usar em um projeto

Dentro da raiz ou de um subdiretório do projeto:

```bash
my-tools init --profile search-experimental
my-tools enable search --provider siftr --allow-remote
my-tools search "onde o cancelamento é processado?" --json --stats
my-tools search "onde o cancelamento é processado?" --glob 'src/*.ts' --top 5 --json --stats
my-tools disable search
```

`init` não habilita capacidades. `enable search` sem `--allow-remote` também não
autoriza envio: a execução é bloqueada até a configuração permitir esse uso.
O opt-in deve corresponder à autorização real para os dados do projeto.
Não use como autorização para enviar código de terceiros/clientes sem permissão.

`--glob` limita os arquivos elegíveis antes do ranking e pode ser repetido.
Os padrões são relativos à raiz; `src/*.ts` também alcança subdiretórios no
matching do Siftr. Sem esse argumento, a busca mantém o escopo upstream padrão.
O filtro não identifica segredos dentro do código. Use uma cópia saneada quando
o checkout misturar código com dados privados. `--top 5` limita resultados,
mas não limita sozinho todos os arquivos examinados ou enviados.

A configuração `.my-tools.json` contém provider, versão, enabled e allow_remote_data.
Ela não pode conter credenciais. Por padrão, `version: approved` acompanha a versão
ativa aceita localmente. `enable search --pin SHA_COMPLETO --allow-remote` fixa uma
versão instalada e aceita, isolando o projeto de atualizações futuras.
Configuração não atravessa uma raiz Git/worktree. `--project DIRETORIO` vem antes
do subcomando, por exemplo `my-tools --project ./exemplo status`.

Disponibilizar o launcher não garante descoberta pelo agente. Na primeira sessão,
peça a execução de `my-tools status` e da capacidade necessária. O CLI é usável por
uma ferramenta de shell permitida; o alcance no desktop/cloud precisa de verificação
no ambiente consumidor. Links locais não se sincronizam para outra máquina.

## Atualização e recuperação

```bash
my-tools outdated --all
my-tools update --all
my-tools update siftr --accept SHA_COMPLETO_DO_CANDIDATO
my-tools rollback siftr
```

`outdated` prefere a maior tag estável `X.Y.Z`; sem tags estáveis, consulta a branch
registrada e devolve seu SHA. `update` prepara o candidato em runtime separado,
valida contrato/integridade e executa a suite offline do upstream. A versão ativa
continua disponível enquanto isso acontece. SHA novo não aprovado no catálogo
fica em `review_required`; `--accept` aceita uma única revisão explicitamente.
Um SHA diferente do candidato atual é recusado. O estado experimental da ferramenta
permanece até existir evidência de benefício e qualidade.

Atualizar não equivale a uma auditoria do código upstream. Leia as diferenças
antes de testar/aceitar novas revisões: as verificações executam código de terceiros.
As verificações retiram credenciais do ambiente e bloqueiam transportes socket
Python, mas isso não é sandbox de sistema contra código hostil.

Uma nova revisão aprovada em `tools.json` pode ser aplicada por `update --all`
sem aceitar o SHA manualmente. Um candidato incompatível não substitui o ativo.
O lote informa falhas/pendências por ferramenta, sem prometer transação global.
Rollback verifica a versão anterior antes de alternar. Pins de projetos permanecem.
Runtimes antigos são preservados, sem coleta automática que possa invalidar pins.
Veja [atualizações](docs/updates.md).

Para atualizar o próprio controlador, com checkout limpo: `git pull --ff-only`,
rode os testes e o check público. O link acompanha esse checkout; o diagnóstico
do adaptador detecta incompatibilidade. Isso é separado de atualizar ferramentas.

## Diagnóstico e remoção

- `status`: estado e configuração efetiva; sem inferência ou suite completa.
- `doctor`: integridade, contrato CLI e suite offline; presença de credencial não
  comprova autenticação, saldo nem disponibilidade do serviço.
- `uninstall`: plano; `uninstall --apply` remove somente o launcher próprio.
- `disable search`: desliga a capacidade apenas no projeto atual.

Uninstall preserva configurações, runtimes e resultados. Antes de mover o checkout,
remova o launcher próprio e recrie-o no novo local. Instalações em outros ambientes
precisam de checkout e setup próprios.

## Avaliar benefício

```bash
my-tools compare benchmarks/examples/baseline.json benchmarks/examples/candidate.json
```

Os exemplos são **sintéticos**, não benchmarks de produtividade. O comparador exige
casos e ambiente equivalentes, inclui falhas/bloqueios, aponta regressões e mantém
tokens ausentes como desconhecidos. Protocolos e fixtures reutilizáveis ficam aqui;
resultados reais permanecem nos registros autorizados do projeto.
Veja [protocolo de busca](benchmarks/protocols/search.md), [arquitetura](docs/architecture.md)
e [integração com skills](docs/skills.md).

O [fluxo de busca](docs/search-workflow.md) descreve os comandos, limites de
escopo e decisão proporcional entre Siftr e rg.

## Escopo da versão 0.1

Somente search/Siftr tem implementação. Redução de logs, seleção de testes,
navegador, MCP, hooks e roteamento de modelos serão integrações separadas depois
dos respectivos pilotos. Não há atualização agendada, migração de memória,
ativação automática em projetos ou promessa de economia de cota ChatGPT.

Licença MIT para este controlador; ferramentas externas preservam suas licenças.
Proveniência e limites estão em [NOTICE.md](NOTICE.md) e [validation](docs/validation.md).
