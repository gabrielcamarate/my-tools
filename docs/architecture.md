# Arquitetura

```text
my-tools: catálogo/SHA → fonte verificada → uv tool install → entrypoint oficial
cliente MCP → siftr mcp → handlers oficiais → provedor → resultado ao agente
```

O gestor não participa das chamadas do agente. Não há proxy, cadastro de chave próprio, perfis ou configuração por projeto. O catálogo registra origem, licença, SHA aceito e instalador. O my-skills orienta a escolha das ferramentas oficiais; plugins podem fornecer suas próprias skills upstream.

`state.json` registra versões aceitas, ativa e anterior. `tools/<nome>/<sha>/` contém fonte Git verificada, hashes e um Python isolado usado somente para checagens offline. Siftr não altera operações ou carregamento de credenciais upstream. Pruner aplica o patch de provedor documentado, com hash próprio além do SHA upstream. `native/<nome>/<sha>/` contém a instalação oficial gerada pelo uv.

`native.json` registra comando estável e SHA instalado. Atualização/rollback de ferramenta integrada verifica o contrato MCP antes de trocar o symlink. Processos existentes precisam reconectar. Persistência usa replace atômico e lock POSIX; restauração entre arquivos é compensatória. `doctor` detecta divergência; `integrate --apply` reconcilia a revisão aceita.

`plugins.json` registra a fonte aceita do plugin Codex. Para Jev Pruner, a fonte é compilada com npm e vinculada em `plugins/jev-pruner`. A integração registra o marketplace local e o plugin oficial; o cache é reinstalado a cada troca de SHA. O gestor confere o cache e restaura a versão anterior em falhas recuperáveis. Não registra MCP ou inventa chamadas para o Pruner.

## Acrescentar uma ferramenta

1. Definir tarefa, baseline e critério de aceite.
2. Registrar origem HTTPS pública, licença e SHA revisado.
3. Implementar somente o ciclo de instalação/verificação em `installers.py` e registrar a interface oficial em `native.py`.
4. Testar candidato inválido, preservação do ativo, falha de persistência e rollback.
5. Documentar instalação oficial, envio de dados e procedimento de avaliação.
6. Orientar uso nas skills pertinentes e medir tarefas equivalentes.

Não crie aliases de operações. O catálogo inclui somente ferramentas integradas. Instalação não concede autorização de envio de dados, merge ou deploy.

## Limites

Instalação e inferência exigem rede; inferência exige credencial oficial. Venv e checagens offline não são sandbox de segurança contra código hostil. Hashes detectam mudanças acidentais; não protegem de um invasor que controla a conta e os registros. Versões oficiais anteriores são mantidas para rollback. Aceitação técnica não comprova qualidade de decisões nem economia de tokens.

Para Pruner, repair recompila o mesmo SHA em staging e restaura fonte/cache em falha recuperável. Atualização verifica aplicação do patch antes da troca; não tenta traduzir protocolos ou resolver conflitos automaticamente. A configuração OpenRouter preserva a API de decisões tipadas e o motor original.
