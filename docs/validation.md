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
