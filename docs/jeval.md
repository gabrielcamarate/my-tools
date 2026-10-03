# Jeval

Origem: [rlaope/jeval](https://github.com/rlaope/jeval), Apache-2.0, SHA `61bdcccf9038ff898e82f9465d1a979f5d68bc6e`, versão 0.2.0. Fonte intacta. Instalação pelo fluxo oficial de checkout/uv, com lock congelado e ambiente isolado por SHA. Não instalar o pacote PyPI chamado `jeval`.

## Para que serve

Avaliar respostas probabilísticas já produzidas, comparando confiança com rótulos conhecidos. Gera HTML offline, métricas com intervalos, análise por pergunta/segmento e limiares conforme custos declarados. Não procura código, compacta contexto ou executa decisões no lugar do Codex. O benefício é evitar automações confiantes e erradas e escolher onde revisão humana vale a pena. Não medimos redução total de tokens ou tempo de tarefas.

Use ao avaliar/adotar um classificador, comparar mudança de pergunta/modelo ou investigar decisões erradas. Precisa de dados representativos e respostas verificadas. Rótulos silver são concordância, não verdade. Sem rótulos, não há avaliação; com poucos, não há conclusão robusta. Não usar score como acurácia binária. Não implantar limiares automaticamente.

## Comandos oficiais

```bash
my-tools install jeval
my-tools integrate jeval --apply
jeval --version
jeval demo --out-dir /tmp/jeval-demo
jeval ingest decisions.jsonl --root /caminho/avaliacao
jeval report --root /caminho/avaliacao --format md
jeval report --root /caminho/avaliacao
```

Para respostas nativas Jev registradas junto do `request_id`, ingestão e aplicação dos rótulos são duas operações:

```bash
jeval ingest decisions.jsonl --root /caminho/avaliacao --preset jev-native
jeval ingest --root /caminho/avaliacao --labels labels.jsonl --label-field label --label-source human_review --join-on request_id --label-question is_failure
jeval report --root /caminho/avaliacao
```

A chave compartilhada OpenRouter continua nas ferramentas que produzem as decisões. Jeval não faz requisições: nenhum ajuste de provedor ou cópia da chave é necessário. Não ativa `collect.track`, hooks, captura, gates CI ou benchmark automático. Fonte/skills ficam no My Tools; seis links pessoais e seus aliases Claude acompanham versões. As duas skills pessoais apenas orientam uso; a instalação já gerenciada prevalece sobre curl/main ou outros instaladores sugeridos upstream.

## Evidência local em 02/10/2026

- 647 testes upstream passaram na revisão aceita.
- Testes de gestão verificam update/rollback dos treze links, preservação de arquivos externos, compensação em falha de link/persistência, runtime e diagnóstico.
- App-server nativo `skills/list` descobriu as seis skills habilitadas, sem erros. Isso não prova carregamento retroativo em sessões já abertas.
- Uma requisição OpenRouter (`typesafe/jev-1.13`, resposta `typesafe/jev-1.13-20260917`) classificou 16 casos sintéticos, todos corretos. O Jeval recebeu 16 rótulos e mediu ECE 0.076, intervalo 95% 0.041–0.132. Avisou que precisa de 100 registros antes de decidir. É teste da integração, não acurácia representativa.
- Controle artificial: 200 decisões, confiança 0.90, 40 erros inseridos. Acurácia 80%, ECE 0.100 (95% 0.050–0.145); um rótulo silver separado e um registro sem rótulo excluído. Com custos hipotéticos erro=20/revisão=1, recomendou encaminhar todos à revisão. Não são custos/tokens reais nem política implantada.
- Relatórios Markdown levaram 0.366 s e 0.379 s em uma execução local. Não há baseline comparável de tarefa Codex nem alegação de speedup.

[Evidência e relatórios sintéticos](../benchmarks/results/jeval-2026-10-02/README.md).

## Codex Cloud

Usável pela CLI sem MCP, hook ou segredo: o ambiente precisa de Git, uv/Python, acesso de preparação às fontes/dependências, checkout my-tools atualizado, `install`/`integrate`, PATH e arquivos rotulados autorizados. A avaliação funciona offline depois de instalada. Com os três repositórios presentes, o setup ainda precisa executar os dois comandos de gestão e orientar a descoberta das skills. A documentação de [skills Codex](https://developers.openai.com/codex/skills) distingue instalação e descoberta; links locais não são transportados pelo Git.

Uma instalação em HOME temporário sem chave gerou o demo e verificou os links. É prova de portabilidade local, não execução no host Cloud. Não alteramos/publicamos ambientes Cloud nesta adoção. Skills/instruções específicas de ambientes existentes precisam consumir a nova preparação; atualizar Git sozinho não cria runtime pessoal.

## Recuperação e atualização

`my-tools outdated jeval`, `my-tools update jeval` e aceitação explícita do SHA candidato seguem o ciclo do gestor; candidatos sem revisão/aceitação não substituem o ativo. `my-tools rollback jeval` requer uma revisão anterior aceita e válida. Hash divergente interrompe uso gerenciado; preservar runtime/arquivos para diagnóstico, sem reinstalar sobre arquivos externos. A instalação inicial não tem versão anterior para rollback.
