# Fast Jev Compaction com OpenRouter

Origem: https://github.com/tamaratran/fast-jev-compaction. MIT, revisão aceita `e3f262a7f4d42bd8dd32ced30d26176f7cb545b0`, plugin 0.3.0. Interface original: plugin Claude Code com function hooks (`session.compact` e `turn.complete`); não é MCP nem skill.

## Instalação

```bash
my-tools install fast-jev-compaction
my-tools integrate fast-jev-compaction --apply
my-tools doctor
```

A instalação busca o SHA aceito, aplica `patches/fast-jev-compaction-openrouter.patch` com `git apply --check`, executa `npm ci --ignore-scripts`, typecheck e os testes upstream e do provedor com HOME temporário e sem credencial. Registra hashes da fonte e do patch. A integração adiciona a fonte gerenciada como marketplace local do Claude Code, instala `fast-jev-compaction@fast-jev-compaction` no escopo do usuário, confere byte a byte o cache do plugin (`.claude-plugin`, `hooks`, `src`) e define `env.CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1` em `~/.claude/settings.json`. As demais chaves e os hooks existentes, como os do AI-Memory, permanecem intactos. Após `update`/`rollback`, execute `integrate --apply` de novo.

## Provedor

O patch altera somente o transporte e a origem da chave no adaptador `hooks/fast-jev.ts`, o padrão de modelo no manifesto, a documentação do hook e os testes. Envia os mesmos `state`/`questions` tipados para `https://openrouter.ai/api/alpha/decisions` com `typesafe/jev-1.13`. Não altera `src/` (estado, perguntas, limiares, decisões, parser) nem o fallback.

Ordem da chave: opção sensível `apiKey` do plugin, `OPENROUTER_API_KEY` do processo e, por fim, o arquivo privado `~/.config/siftr/.env`, lido por `$.fs.read`. Uma variável explicitamente vazia desliga o arquivo. A chave não é copiada para settings, plugin ou ambiente dos processos filhos.

## Ativação e prova de uso

Function hooks são early access. Além da flag local, o Claude Code consulta um rollout remoto (`tengu_plugin_hooks_modules`). Quando ele está desligado, o módulo não carrega e o `/compact` permanece nativo. Em `claude -p`, o aviso aparece no stderr: `fast-jev-compaction: hooks module not loaded: ...`. O valor remoto só é atualizado com sessão autenticada. Não force overrides locais desse rollout.

Com o módulo carregado, reinicie o Claude Code ou use `/reload-plugins`. Depois de `/compact`:

- uso de Jev: toast/log `kept N/M messages, no summary (X% reduction; ... in K request(s))`, seguido de linhas `decisions:`. Não há mensagem de resumo na transcrição;
- fallback: `fallback to built-in summary (<motivo>)` e o resumo nativo aparece.

`claude --debug` registra os logs do hook. Sem nenhuma das duas mensagens, o hook não rodou.

## Envio de dados

Cada compactação envia ao OpenRouter/TypeSafe o histórico da sessão (textos e chamadas de ferramentas, saídas abreviadas). Use somente quando esse histórico estiver autorizado para processamento externo. O hook `turn.complete` pede compactação automaticamente a partir de 60% do contexto.

## Evidência de 07/10/2026

`node --import tsx scripts/test_compaction_live.mjs <source>` usa o `register` real do hook com um `$` mínimo, histórico técnico inteiramente sintético e fetch real:

- live: HTTP 200 de `openrouter.ai`, modelo `typesafe/jev-1.13`, 18/18 respostas, 1,05 s; 26 → 8 mensagens; 44.858 → 5.115 caracteres. Textos de usuário/assistente e o resultado recente foram preservados.
- fallback: chave ausente, HTTP 401 e histórico curto delegaram ao resumo nativo (`next`).

`claude plugin validate` do Claude Code 2.1.290 aceitou o módulo. Hooks: `session.compact` e `turn.complete`. Leituras de ambiente: `HOME` e `OPENROUTER_API_KEY`. Nenhuma escrita de ambiente. A primeira tentativa no motor foi recusada porque o rollout remoto estava desligado no cache e o OAuth do CLI tinha expirado. Depois que o rollout passou a `true`, uma sessão sintética nova com o plugin instalado executou `/compact` (`claude -p --debug-file`). O resultado foi `hooks module ... loaded`, POST para OpenRouter com HTTP 200 em 991 ms e `kept 8/22 messages, no summary (87% reduction ...)`. O log também mostrou `session.compact (manual): a hook's 8 messages stand ... core never ran`, ou seja, não houve resumo nativo.
