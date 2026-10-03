# Correções de adoção local em 03/10/2026

## Falhas corrigidas nos chamadores

- Siftr: glob com chaves não tem expansão em fnmatch. Perguntas focadas, raiz
  estreita ou filtros CLI repetidos evitam excluir todos os arquivos.
- Skills: guia compartilhado agora pode ser lido através dos links instalados;
  o validador permite apenas o destino interno canônico e rejeita escapes.
- Pruner: perfil pessoal explícito para histórico técnico elegível, mantido fora
  dos repositórios. Categorias excluídas continuam impedindo envio externo.
- Browser: smoke funcional exige interface oficial, mantendo suites e provas
  visuais existentes como gates independentes.

## Aceitação real sintética

| Interface | Resultado | Limite |
|---|---|---|
| Siftr CLI | Glob inválido: 0 arquivos e 0 requisições. Filtros repetidos: 2 arquivos, 2 requisições, credits.ts em primeiro com 0,92; 0,85s | Exemplo sintético, não economia de tarefa |
| Pruner wrapper e hook oficial | 101.632 para 12.596 bytes (87,6%); quatro diagnósticos preservados, stderr/status iguais, arquivo original com hash idêntico; 1,84s | Hook chamado com evento sintético, não seleção automática |
| Jev Browser CLI | Formulário salvo com valores exatos, uma submissão verificada no servidor; 2,28s | Sessão isolada sintética, não catálogo MCP ou obediência de agente |

Comandos reproduzíveis (usar caminhos da instalação upstream ativa):

```sh
python3 scripts/test_siftr_globs_live.py
node scripts/test_pruner_live.mjs PLUGIN_ROOT
node scripts/test_browser_cli_live.mjs BROWSER_SOURCE
```

As chamadas reutilizaram OpenRouter; nenhuma chave foi escrita nos testes ou
publicada. Fixtures temporárias e sessões próprias foram removidas. Nenhum engine
upstream, gate de projeto, hook de memória ou configuração Cloud foi alterado.

A instalação contém 15 ferramentas; nenhuma substitui a compactação nativa do
Codex. O Pruner reduz stdout; o hook PreCompact local pertence ao AI-Memory.
Uso automático e benefício líquido precisam ser aferidos na próxima tarefa real.
Regras mais explícitas não são interceptação obrigatória de todas as chamadas.
