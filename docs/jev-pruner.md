# Jev Pruner

Origem: https://github.com/tamaratran/jev-pruner. MIT, revisão aceita `edbc60262a5edc07e18d646c1a3f8a9f0ae868c5`, plugin upstream 0.1.0. Integração experimental, oficial e sem patch; não é um MCP.

## Ciclo gerenciado

```bash
my-tools install jev-pruner
my-tools integrate jev-pruner --apply
my-tools outdated --all
my-tools update jev-pruner --accept SHA_COMPLETO_REVISADO
my-tools rollback jev-pruner
my-tools doctor
```

`install` fixa fonte e dependências pelo Git/lock, compila TypeScript e verifica wrapper, manifestos e suíte upstream. Sem alteração do engine de poda. O gestor não possui comando de poda próprio e não injeta credenciais.

`integrate` usa `codex plugin marketplace add` e `codex plugin add jev-pruner@jev-pruner-codex`. O link local aponta para a fonte aceita. Codex resolve esse link para a revisão concreta e copia arquivos para seu cache. A atualização remove somente o plugin/marketplace gerenciado, registra a nova fonte e reinstala o cache. Compara a árvore compilada, hook e skill byte a byte, pois SHAs diferentes podem declarar a mesma versão 0.1.0.

Atualização ou falha de registro tenta restaurar fonte e cache anteriores. Não é transação global nem garantia contra falhas múltiplas de disco/processo. Doctor diagnostica divergência; integrate --apply reconcilia. Instalação externa ou desabilitada no cliente não é sobrescrita/reabilitada implicitamente. Reinicie sessões e revise hooks alterados.

## Uso e limites

A skill original `jev-pruner` executa o wrapper upstream no shell nativo. Pruner requer Node, `TYPESAFE_API_KEY`, rede permitida para api.typesafe.ai e hook confiado para encontrar a transcrição correta. Ausência de qualquer requisito preserva stdout; não invente marcadores nem ganho.

O wrapper preserva stderr e exit status, não intercepta outros comandos e não serve para servidores/TTY ou chamadas aninhadas que exigem dados estruturados. Stdout é bufferizado até conclusão, com streaming completo acima de 8 MiB. Somente resultados acima de 10 mil tokens estimados são elegíveis. Saídas protegidas e comandos com falha podem continuar completos.

Jev recebe histórico e saída. A autorização deve abranger a conversa inteira que entra na avaliação; não basta autorizar um arquivo de log. Filtragem de credenciais do comando atual não é saneamento de histórico. Nunca use transcrições com dados pessoais/financeiros, segredos ou documentos privados sem autorização específica. Teste em conversa dedicada sintética/pública. Não altere captura AI-Memory para contornar isso.

Os originais arquivados permitem recuperação; não são enviados ao Git. Ler o arquivo do rodapé recupera trechos sem executar novamente. Não eleve limites de host ou sandbox como efeito da instalação. A recomendação upstream de 30 mil tokens é opt-in por sessão e não foi aplicada globalmente.

## Evidência

Instalação oficial compilada, testes/typecheck upstream e wrapper sem chave passaram localmente. Codex CLI 0.159.2 registrou o plugin e seu cache corresponde à fonte aceita. Atualização e rollback de duas fontes com mesma versão foram exercitados no cliente real com CODEX_HOME isolado. Testes do controlador cobrem falha de instalação, persistência, cache alterado e preservação de instalações de terceiros/desabilitadas.

Chave TypeSafe não estava no ambiente do executor. Nenhuma inferência ou poda live foi validada nesta instalação; não há benchmark de economia. Confiança no hook, desktop e Cloud permanecem não verificados. São condições de uso, não resultados presumidos de instalar.
