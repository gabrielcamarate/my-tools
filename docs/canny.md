# Canny: evidência de conclusão

Integração experimental de 02/10/2026. Origem [qkal/Canny](https://github.com/qkal/Canny), MIT, versão 0.3.0, SHA `f2c5e53779445d60dc4a09d2dbced2308fccb820`.

## Funcionamento e ativação

A CLI/hook oficial registra edições e comandos. Ao concluir depois de alterar código, exige um check reconhecido passando após a última edição. Jev julga mensagens/regras; evidência determinística decide os bloqueios. Também detecta alguns segredos, remoções de testes e repetição de falhas.

```bash
my-tools install canny
my-tools integrate canny --apply
# Na raiz do projeto autorizado:
canny init --codex
# Revisar hooks no Codex CLI com /hooks e confiar no projeto.
canny status
canny replay
# Remover somente entradas Canny do projeto:
canny remove
```

O upstream não contém skill nem MCP nesta revisão. A instalação gerenciada publica somente a CLI. A adoção inicial testou ativação em fixtures. Em 02/10/2026, Gabriel autorizou a configuração pessoal: os quatro hooks Codex foram instalados com `canny init --codex --global`, revisados e confiados pela API oficial do cliente. Hooks e confiança preexistentes foram preservados. A descoberta local foi confirmada nos cinco checkouts, sem erros. Uma sessão desktop já aberta ainda precisa recarregar seus hooks; não se presume carregamento retroativo. Isso descreve o host validado, não ativa hooks pessoais de quem clonar o repositório. O modo automático depende de projeto trusted, hooks revisados/confiados e sessão que os carregou. `status` sem eventos não significa supervisão funcionando. Instruções nas skills orientam uso quando já ativo, sem substituir o mecanismo.

## Provedor e dados

Patch mínimo autorizado: endpoint `https://openrouter.ai/api/alpha/decisions`, modelo `typesafe/jev-1.13`, mesma `OPENROUTER_API_KEY`. Na ausência da variável, reutiliza o arquivo privado do Siftr somente quando regular e sem permissões para grupo/outros. Variável explicitamente vazia desativa esse fallback. Não copia chave por ferramenta/projeto. URL/modelo/timeout continuam configuráveis via `CANNY_JEV_URL`, `CANNY_JEV_MODEL`, `CANNY_JEV_TIMEOUT_MS`, inclusive proxy Cloud compatível. O hash de cache inclui endpoint e corpo, evitando reaproveitar julgamentos de destinos diferentes.

Contrato `state/questions/answers.noul` preservado conforme [OpenRouter](https://openrouter.ai/blog/tutorials/how-to-use-jev/). Engine de checks/eventos/regras/install/ledger e limiares permanecem upstream. Instalação registra hashes de fonte, compilação e patch; conflito ou contrato alterado bloqueia candidato, preservando ativo. Scripts de pacotes não recebem a chave do ambiente.

A autorização de uso deve cobrir os dados: mensagens de conclusão e trechos editados/regras podem ser enviados ao provedor. O ledger guarda comandos/caminhos/resultados; comandos podem conter dados sensíveis. O cache Jev guarda **o corpo da consulta**, podendo conter código/mensagens/regras, em `CANNY_HOME` ou `~/.canny`, com arquivos 0600. Não é correto afirmar que todos os arquivos Canny contêm apenas metadados. Não publicar cache/ledger/transcrições nem usar fixtures privadas como teste. Nenhum dado de projetos consumidores foi enviado nesta adoção.

## Limites

- Reconhece `Bash` e `apply_patch` no Codex; não prova cobertura de qualquer ferramenta/MCP/editor externo. Algumas edições por shell podem escapar ao parser.
- Um test/build/lint/typecheck reconhecido após edição pode liberar conclusão, mas não prova todos os critérios de aceitação ou produção.
- Sem chave/rede conserva a regra determinística de conclusão. Crash do hook falha aberto e escreve `errors.log`; confira `canny status`.
- O padrão pode liberar a segunda parada sem fatos novos com **aviso**. `strict` é uma configuração upstream opcional, não foi imposto pela integração. Não enfraquecer regras para vencer um bloqueio.
- Não substitui revisão técnica, autorização de PR/merge/deploy ou gates finais. Não reduz automaticamente logs/testes/tokens.

## Testes e medição

[Resultados sintéticos](../benchmarks/results/canny-2026-10-02/results.json) e [sessão Codex CLI](../benchmarks/results/canny-2026-10-02/native-codex.json).

256 testes upstream/provedor passaram; type-check, lint, cobertura e smoke passaram. Controlador validou conflitos, comandos externos, atualização/rollback e restauração após falhas. Fixture live usando CLI oficial com payloads Codex:

| Caso | Resultado |
|---|---|
| Edição, conclusão sem check | block |
| Teste real falhando | block |
| Correção + teste real passando | allow |
| Sem chave / rede indisponível | block determinístico |
| Outra parada padrão sem fatos novos | warn, não block |
| Reexecução do ledger | 3 decisões reproduzidas |
| init/reinit/remove com hook de terceiro | preservado |

Julgamento real de conclusão em português: 0,99, 376 ms na primeira consulta. O segundo usou cache (0 ms de inferência). Processo/hook completo: aproximadamente 432 ms frio, 55 ms com cache; liberação depois do check, 64 ms. Suíte sintética sem Canny: aproximadamente 109 ms falhando / 115 ms passando. São medições pequenas de caminhos diferentes, **não** comparação de duração total da mesma tarefa com/sem Canny. Não houve economia Codex medida.

Uma nova sessão Codex CLI 0.160.0 isolada passou em 18,19 s: hooks receberam edições/comandos/Stop e liberaram conclusão após `node --test` aprovado. O agente seguiu instruções de verificação e não tentou concluir antes do check; esse teste comprova entrega nativa dos hooks e caminho positivo, não causalidade do bloqueio nessa sessão. Casos negativos foram comprovados por subprocessos da CLI oficial acima. O teste revisado usou bypass de confiança apenas na invocação isolada, sem persistir confiança ou alterar hooks pessoais. Autenticação nativa foi referenciada por link temporário, sem cópia de valores. Recursos próprios foram removidos.

Reproduzir somente com dados sintéticos e credencial compartilhada disponíveis:

```bash
node benchmarks/run-canny.mjs local-results/canny
node benchmarks/run-canny-codex.mjs
```

O segundo requer autenticação local nativa do Codex, usa um HOME isolado e tem timeout de 120 s. Não usar seu bypass para habilitar hooks pessoais em geral. Evidências publicadas são apenas resultados sintéticos saneados.

## Cloud

Ter projeto, my-skills e my-tools permite preparar CLI/runtime/credencial, mas não injeta hooks no host da conversa. A [documentação atual de hooks](https://learn.chatgpt.com/docs/hooks) informa que hooks command/local/plugin não são suportados com orquestração Cloud. Portanto a **supervisão automática desta ferramenta está bloqueada nesse fluxo**; `status/replay` só analisam um ledger existente e não interceptam a conversa. Não converter essa limitação numa promessa de uso integral por CLI. Nenhum teste Cloud real foi executado nesta adoção.

## Atualização

```bash
my-tools outdated canny
my-tools update canny
# Se revisão explícita for exigida, revisar candidato antes de --accept SHA_COMPLETO.
my-tools rollback canny
```

CLI estável acompanha revisão aceita; hooks por nome continuam no mesmo entrypoint. Sessões já abertas precisam confirmar carregamento da nova revisão. Alterações de definição do hook exigem nova revisão/confiança pelo cliente. Rollback exige uma versão anterior aceita; esta é a primeira instalação de Canny.
