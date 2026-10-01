# Jev Pruner com OpenRouter

Origem: https://github.com/tamaratran/jev-pruner. MIT, revisão aceita `edbc60262a5edc07e18d646c1a3f8a9f0ae868c5`, plugin upstream 0.1.0. Interface original: plugin Codex, skill e wrapper de shell; não é MCP. O My Tools mantém um pequeno patch de provedor autorizado, sem alterar o motor de poda.

## Instalação e manutenção

```bash
my-tools install jev-pruner
my-tools integrate jev-pruner --apply
my-tools doctor
my-tools outdated --all
my-tools update jev-pruner --accept SHA_COMPLETO_REVISADO
my-tools rollback jev-pruner
```

Instalações anteriores ao ajuste de provedor usam `my-tools repair jev-pruner`, com o plugin gerenciado habilitado. Repair recompila em staging, verifica antes da troca e restaura fonte/cache anteriores em falha recuperável. Não reabilita plugins desabilitados implicitamente. Uma falha múltipla ou interrupção exige reconciliação; não há transação global.

A instalação fixa Git/lock, aplica `patches/jev-pruner-openrouter.patch` com `git apply --check`, compila e executa os testes upstream e de integração. Registra hashes da fonte, compilação e patch. Uma mudança upstream incompatível com o patch impede ativação. Cache do Codex, hook e skill são conferidos byte a byte, pois revisões diferentes podem declarar a mesma versão 0.1.0. Atualizações/rollback reinstalam o cache pelo cliente oficial.

O patch altera URL/modelo, leitura da chave e orientação da skill Codex; os testes que usam credencial fictícia acompanham esse nome. Não altera `output.ts`, decisões/limiares, regras de proteção, particionamento do histórico, parser de respostas, hook ou arquivos de recuperação. A chave é `OPENROUTER_API_KEY`; endpoint `https://openrouter.ai/api/alpha/decisions`; modelo `typesafe/jev-1.13`. São os mesmos `state/questions/answers` tipados, sem converter respostas de chat. Fonte: [OpenRouter Decisions API](https://openrouter.ai/blog/insights/what-is-jev/).

No computador pessoal, o wrapper reutiliza a chave do arquivo privado `~/.config/siftr/.env` quando a variável não está definida. Arquivo precisa ser privado (sem acesso de grupo/outros). Não lê `.env` do projeto, não duplica chave e não imprime seu conteúdo. Variável explicitamente vazia desliga esse fallback. O Cloud recebe a credencial pela configuração própria do ambiente.

## Uso

O agente consulta a skill do plugin `jev-pruner` e executa o comando original:

```sh
node "<plugin-root>/dist/codex/run.js" -- npm test
```

O root aparece em `my-tools status`; a skill do plugin também resolve sua raiz. Use em builds/testes/instalações não interativas com logs grandes. Não intercepta todos os comandos. Não use em servidor/TTY, progresso que precisa ser acompanhado ao vivo, leitura de arquivo completo, diffs, JSON/XML/YAML, conteúdo sensível ou saída consumida por outro programa. Não filtre novamente com Siftr.

Somente stdout acima de 10 mil tokens estimados é elegível. O wrapper bufferiza até conclusão, transmite tudo acima de 8 MiB, preserva stderr e exit status. Comandos que falham permanecem completos. Falta de chave, histórico, rede, arquivo de recuperação ou falha de avaliação também preserva stdout. Saída protegida/uncerta pode permanecer integral. Não declare poda sem marcador de omissão.

O original é salvo em `.jev-pruner/` no workdir (diretório privado, arquivo 600, ignore interno). O rodapé fornece o caminho para recuperação. Texto retido é original, não um resumo gerado. A recuperação evita executar novamente apenas para ler o que foi omitido.

O hook `PreToolUse` registra o caminho da transcrição e o wrapper usa `CODEX_THREAD_ID`. Hooks de plugins precisam de revisão/confiança no cliente: em uma nova sessão CLI, abra `/hooks` e confira o hook do Pruner. Instalar/habilitar não concede confiança automaticamente. [Documentação oficial de hooks](https://learn.chatgpt.com/docs/hooks).

A avaliação envia histórico e stdout ao OpenRouter/TypeSafe. A autorização precisa abranger o histórico que será avaliado; os detectores do comando atual não saneiam mensagens anteriores. Nossos testes live usam uma sessão dedicada inteiramente sintética. Não altere AI-Memory ou permissões do host para fazer poda funcionar.

## Codex Cloud com os três repositórios

Ter projeto, my-skills e my-tools no ambiente fornece os fontes, mas não configura sozinho o runtime. O código é portátil para um ambiente Linux com Node/npm, Git e Python, mas o uso na sessão Cloud depende também de:

1. Instalar/compilar pelo My Tools e registrar o plugin **no cliente do ambiente**, não apenas no desktop. Usar o checkout atualizado do my-skills e seu instalador para tornar as quatro skills descobertas.
2. Disponibilizar a mesma chave como `OPENROUTER_API_KEY` durante a tarefa. No Cloud atual, pode ser uma **network secret** com domínio permitido `openrouter.ai`: programas recebem placeholder e o proxy substitui o valor em HTTPS/443. Não copie a chave do desktop para o Git ou arquivos do projeto. A presença dos três repositórios não transporta configuração pessoal.
3. Permitir rede para `openrouter.ai` e requisições POST durante a tarefa. Rede da preparação não comprova rede do agente.
4. Ter hooks suportados/confiados, `CODEX_THREAD_ID` e transcrição legível no formato compatível com esta revisão upstream. Sem esses requisitos, o wrapper executa e devolve tudo, sem poda.
5. Abrir uma tarefa sintética nova, executar via skill e verificar marcador, original e diagnósticos. Um doctor offline não é essa prova.

Exemplo de preparação, com paths reais dos checkouts definidos pelo ambiente:

```sh
"$MY_TOOLS_REPO/bin/my-tools" install jev-pruner
"$MY_TOOLS_REPO/bin/my-tools" integrate jev-pruner --apply
"$MY_TOOLS_REPO/bin/my-tools" doctor
python3 "$MY_SKILLS_REPO/scripts/skillctl.py" install --target codex --apply
```

Não é preciso um comando `my-tools prune`: a chamada continua sendo o wrapper do plugin. Em runtimes que não disponibilizam hooks/transcrição, esta revisão não oferece poda funcional por esse caminho, mesmo com Node e credencial.

[Cloud atual: variáveis, network secrets e acesso de rede](https://learn.chatgpt.com/docs/environments/cloud-environments). Se o ambiente ainda for **Cloud Legacy**, secrets ficam disponíveis somente na preparação e são removidos antes do agente; um `export` no setup não persiste. Não grave secrets em arquivos para contornar essa remoção. [Cloud Legacy](https://learn.chatgpt.com/docs/environments/cloud-environment).

Não foi executada uma tarefa no Codex Cloud neste piloto. Suporte de runtime e configuração de seu ambiente Cloud continuam condicionais; não declaramos pronto só pela presença dos repositórios.

## Evidência de 30/09/2026

Teste live reproduzível, explicitamente autorizado e sintético:

```sh
node scripts/test_pruner_live.mjs "<plugin-root>"
```

Resultado local: 101.632 → 12.596 bytes; 22.710 → 2.930 tokens estimados; redução de stdout de 87,6%. Artefato Q7, rollback e dois diagnósticos preservados; stderr/exit status idênticos; SHA-256 do original e arquivo de recuperação idênticos; respostas reais `noul`, HTTP 200. O comando simples demorou 0,037 s e o wrapper 1,256 s. Essas medidas são uma fixture, não economia da cota nem velocidade de uma tarefa completa. Chamadas concorrentes não devem ter durações somadas.

Benefício principal: menos logs repetitivos no contexto futuro do Codex, com recuperação integral. Isso não encurta o teste executado e pode acrescentar latência. Avaliar tarefas equivalentes é necessário para medir ganho líquido.

Uma sessão real nova do Codex CLI, com plugin isolado e dados sintéticos, invocou o wrapper e recebeu marcadores de poda; o hook criou o ponteiro de histórico automaticamente e os três valores pedidos foram preservados. O cliente pessoal também exibiu o hook `Plugin - jev-pruner@jev-pruner-codex`, matcher Bash, ativo e Trusted em `/hooks`. Essa inspeção não alterou outros hooks e não prova carregamento de uma sessão desktop já aberta.

Bootstrap também passou em HOME/CODEX_HOME/My Tools storage novos e isolados: instalação, compilação, testes, cache e links das 23 skills, sem copiar chave pessoal. Comparação com Git upstream confirmou bytes idênticos em output.ts, jev.ts, secrets.ts, codex/history.ts, codex/context.ts e codex/hook.ts. É um teste local de preparação portátil, não uma tarefa Cloud.
