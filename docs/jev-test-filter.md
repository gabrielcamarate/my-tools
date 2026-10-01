# Jev Test Filter

Origem: https://github.com/mizchi/jev-test-filter, MIT, versão 0.1.3,
SHA `955bdf4e20ff49c3dac0b5b3eee5df0278d5be87`.

## Interface e provedor

A CLI oficial pontua a relevância de testes para um Git diff e passa argv ao runner
com `--exec`, sem shell intermediário. A skill upstream completa é vinculada na
pasta pessoal do Codex; o My Tools gerencia somente instalação e versões.

O patch `patches/jev-test-filter-openrouter.patch` configura
`https://openrouter.ai/api/alpha/decisions`, `typesafe/jev-1.13` e
`OPENROUTER_API_KEY`. Usa o contrato score do provedor, sem converter chat.
Os algoritmos de seleção, critérios, limiares, fallback, concorrência, replay e
argv não foram modificados. Conflito de patch impede ativação.
Contrato: [OpenRouter Decisions](https://openrouter.ai/blog/insights/what-is-jev/).

A chave vem do ambiente, ou do arquivo pessoal privado já utilizado pelo Siftr
quando a variável está ausente. Valor explicitamente vazio desliga o fallback.
O arquivo deve ser regular e ter permissões sem acesso de grupo/outros. Não lê
`.env` dos projetos, não copia nem grava chave. O diff e as definições de testes
vão ao OpenRouter; isto requer autorização para esses dados. Não precisa de
transcrição de conversa ou hook.

## Uso

```bash
my-tools install jev-test-filter
my-tools integrate jev-test-filter --apply
my-tools doctor
# Dentro do projeto: mudanças rastreadas locais contra HEAD
jev-test-filter --format node --exec -- node --test
# Alterações desde uma referência confirmada
jev-test-filter --base origin/main --exec -- vitest run
jev-test-filter --base origin/main --format playwright --exec -- npx playwright test
# Inspeção, sem executar testes
jev-test-filter --format node --json
# Reavaliar um registro sem rede; apenas para o mesmo candidato/entradas
jev-test-filter --replay .jev-test-filter/last.json --cutoff 1.0 --json
```

Confirme a base com Git e leia a skill upstream antes de construir comandos.
Sem `--base`, compara o working tree ao HEAD (ou índice com `--staged`).
`--base` compara commits desde a merge-base até HEAD, excluindo edições ainda
não commitadas. Não use essa variante para validar uma mudança só local.
Arquivos novos ainda não rastreados não entram no diff; adicionar ao índice
quando autorizado. Rust e Go precisam dos runtimes; múltiplos frameworks exigem
`--format`. Não suporta pytest. `.jev-test-filter/` armazena registros locais;
ignore-os no Git do consumidor se autorizado, pois podem conter testes privados.
Não instalamos hooks/pre-push nem alteramos CI dos projetos.

Seleção é probabilística e serve apenas à iteração em suítes lentas. API sem
chave/erro retorna execução ampla; respostas ausentes selecionam os testes sem
resposta. Caso de framework misto requer decisão, não fallback silencioso.
Sucesso de uma seleção não dispensa checks finais, CI ou smoke obrigatórios.
Skills pertinentes no my-skills: `gabriel-github-resolution`,
`gabriel-loop-engineering`, `gabriel-verification-planning`.

## Evidência em 30/09/2026

Instalação em HOME vazio com armazenamento isolado também passou, com CLI e
skill completas e doctor da ferramenta ready_offline; isso é portabilidade local.

164 testes upstream passaram; um foi ignorado pelo upstream. O controlador passou
52 testes, incluindo preservação de instalação externa, conflito do patch, falha
de troca parcial, persistência, reconciliação e rollback dos links CLI/skill.

Fixture pública `benchmarks/fixtures/test-filter-project`: 20 testes Node, três
regressões de devolução de créditos (uma chamada indireta), incluindo nome em
português. O Jev selecionou os três em três scorings live. Ambos os runners
retornaram exit 1 para a regressão. O baseline saudável retorna 0.

| Medição sintética, uma execução por variante | Suíte completa | CLI + API + selecionados |
|---|---:|---:|
| Testes rápidos (sem atraso intencional) | 0,159 s | 0,851 s |
| 100 ms de atraso configurado por teste | 2,129 s | 0,953 s |

O atraso simula I/O e não representa um projeto real. Selecionar 3/20 evita 17
execuções; o ganho medido da variante lenta foi 55,2%. A variante rápida ficou
mais lenta. Sem chave, selecionou tudo; alteração só de documentação selecionou
zero; replay não chamou API. A primeira chamada reportou 4.442 tokens de entrada,
344 de saída e 610 ms no cliente. `spent.usd` é estimativa do upstream pelo preço
unitário, não extrato de cobrança. Menos execução/log pode reduzir contexto e
retrabalho, mas não medimos economia total de tokens Codex.

## Codex Cloud com os três repositórios

Compatível em princípio; execução real no Cloud ainda não validada. Prepare
Python 3.11+, Node 24+ e pnpm no ambiente. No checkout My Tools, execute
`python3 bin/my-tools setup --apply`, instale e integre o Test Filter pelos
comandos acima. No my-skills atualizado, rode o instalador com
`--target codex --apply`. Garanta `~/.local/bin` no PATH. Verifique que o ambiente
descobre a skill upstream e que a base Git/test runner existem.

No Cloud atual, o ambiente precisa solicitar `OPENROUTER_API_KEY`; o cofre pessoal
sozinho não fornece variáveis não solicitadas. Configure o valor e o acesso HTTPS
POST a `openrouter.ai` durante a tarefa. O cliente deve usar o proxy de rede do
ambiente. Para o fetch nativo do Node 24+, configure `NODE_USE_ENV_PROXY=1`
quando houver HTTP_PROXY/HTTPS_PROXY no ambiente, mantendo os certificados
exigidos por ele. [Suporte Node ao proxy](https://nodejs.org/learn/http/enterprise-network-configuration).
Valide uma chamada real no setup e em uma tarefa nova antes de afirmar
aceitação Cloud. Chaves pessoais/links do desktop não acompanham os repositórios.

[Documentação oficial Cloud](https://learn.chatgpt.com/docs/environments/cloud-environments)
e [descoberta de skills](https://learn.chatgpt.com/docs/build-skills).
Uma sessão nova do Codex CLI (GPT-6 Luna, esforço low) descobriu a skill pessoal,
leu suas instruções, executou a CLI com `--exec` e reteve as três falhas esperadas.
Isso valida o fluxo local explícito, não seleção implícita garantida nem Cloud.
Não depende de hooks ou histórico do Pruner. Cloud Legacy tem política distinta
para secrets disponíveis só no setup; não persistir chave em arquivo para contornar
essa restrição. Ter os três repositórios presentes não substitui a preparação.

## Repetir a avaliação sintética

`node benchmarks/run-test-filter.mjs DIRETORIO_LOCAL_DE_EVIDENCIAS` instala uma
fixture Git temporária, chama a CLI oficial com a chave compartilhada, compara
seleção/execução e grava resultados no diretório indicado. Requer envio autorizado
da fixture pública. Não coleta benchmarks de tarefas automaticamente.

## Atualização

```bash
my-tools outdated --all
my-tools update jev-test-filter
# Depois de revisão explícita do candidato
my-tools update jev-test-filter --accept SHA_COMPLETO_REVISADO
my-tools rollback jev-test-filter
my-tools doctor
```

Nova revisão não aceita segue `review_required`. Fonte e compilação têm hashes
vinculados ao SHA e ao patch. Os links oficiais acompanham o SHA aceito; falhas
recuperáveis restauram o anterior. Uma interrupção abrupta pode exigir `doctor`
e `integrate jev-test-filter --apply` para reconciliar o estado.
