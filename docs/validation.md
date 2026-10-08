# Validação

O CI verifica o controlador em Python 3.11 e 3.14, sem credenciais ou inferência.

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_public.py
my-tools doctor
```

A suíte cobre origem/SHA e integridade, revisão pendente, alteração incompatível upstream, candidato inválido, preservação de comandos de terceiros, lock, falha de persistência, compensação e rollback. Descoberta stdio verifica os quatro nomes MCP oficiais. Exemplos do comparador são sintéticos.

Em 30/09/2026, chamadas das quatro ferramentas oficiais foram verificadas com código público e saída sintética. Uma sessão nova do Codex usou semantic_search antes de busca local ao invocar uma skill de descoberta. Registros detalhados ficam no consumidor autorizado; não comprovam seleção universal, carregamento em Cloud ou ganho de produtividade comparável.

Na versão 0.3.0 foram removidos a CLI de busca adaptada, cadastro próprio de chaves, perfis e configuração por projeto. O ciclo de instalação verifica fonte e interface upstream sem modificar suas operações ou carregamento de credenciais. Os testes de instalação e recuperação continuam obrigatórios.

Em 30/09/2026, v0.5.0: 45 testes do controlador e check de publicação passaram; compilação, typecheck, testes upstream e dois testes do provedor passaram. Teste live sintético OpenRouter e sessão real do Codex CLI confirmaram poda, linhas necessárias, stderr, status e recuperação original. O teste do agente usou apenas o Pruner em CODEX_HOME isolado e confiança de hook para aquela invocação; não alterou a confiança global. Não é prova de execução em Cloud nem medição comparável de economia total. Veja docs/jev-pruner.md.

## 2026-10-02 — Descoberta e escolha das ferramentas

- Registro CLI legado compatível; integrate acrescenta alias Claude estável sem copiar fonte.
- 71 testes do controlador PASS: update/rollback, preflight de terceiros, falha parcial e de persistência, migração idempotente e remoção de alias novo na compensação.
- Check público e diff check PASS. Doctor local: quatro ferramentas ready_offline; duas skills upstream com alias Claude linked.
- Siftr chamado pelo MCP numa fixture sintética pública: quatro arquivos pesquisados; resultados conferidos como sugestões, não prova exaustiva.
- Pruner no wrapper oficial com histórico/saída sintéticos: 22.710 para 2.938 tokens estimados, marcador de poda presente, quatro diagnósticos obrigatórios preservados, stderr/exit status e original preservados. Pasta própria removida ao final. Não é economia de tokens da tarefa inteira nem teste de histórico privado desta sessão.
- Jev Browser por MCP isolado: cenário sintético com dados aninhados complete, cinco campos no readback, unobserved vazio, registro conferido independentemente e uma submissão. Browser/MCP/servidor de fixture próprios encerrados.
- Test Filter live em fixture sintética: 3/20 testes selecionados; três regressões preservadas, sem chave segue fallback; cleanup próprio concluído. Não dispensa gates finais.
- Nenhuma prova de seleção implícita universal, aceitação Cloud ou redução de duração de tarefas reais. Configuração de cliente pessoal e credenciais continuam fora do Git.

## 2026-10-02 — Jeval 0.2.0

87 testes do controlador passaram, incluindo nove do ciclo Jeval; check público e diff check passaram. Os 647 testes upstream passaram na adoção. Smoke do instalador usa CLI/version/demo em ambiente temporário; não repete a suíte de 647 testes em cada diagnóstico. Avaliação offline repetível valida acurácia/ECE do controle, concordância HTML/Markdown, recusa de bins inválidos e falta de labels. Teste OpenRouter gerou apenas casos sintéticos; seis skills habilitadas encontradas pelo app-server nativo. HOME limpo passou, sem provar execução Cloud. Veja docs/jeval.md e benchmarks/results/jeval-2026-10-02/.

## Correções locais de adoção: 03/10/2026

Ver [aceitação sintética reproduzível](local-adoption.md). Nenhum percentual
de redução de stdout foi convertido em economia total de tokens ou cota Codex.

Em 07/10/2026: Fast Jev Compaction instalado no SHA `e3f262a`, typecheck e 31 testes upstream/provedor passaram, `claude plugin validate` (2.1.290) aceitou o módulo. Teste live sintético via OpenRouter reduziu 26 → 8 mensagens e confirmou três fallbacks. Depois que o rollout remoto foi liberado, `/compact` no motor manteve 8 de 22 mensagens sem resumo nativo. Veja docs/fast-jev-compaction.md.
