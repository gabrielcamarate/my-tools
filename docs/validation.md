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
