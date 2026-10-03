# my-tools

Repositório público de programas reutilizáveis e protocolos de avaliação.

- Leia README.md e docs/architecture.md antes de alterar contratos.
- Python 3.11+, biblioteca padrão no controlador. Linux é o alvo validado.
- Não copie ferramentas upstream: registre origem, licença, SHA e instalador oficial.
- Mudanças em instalação/atualização exigem testes de falha e recuperação.
- Execute python3 -m unittest discover -s tests -v e python3 scripts/check_public.py.
- Preserve versões ativas aceitas e arquivos de terceiros.
- Mantenha AGENTS.md e CLAUDE.md iguais.
- Não publique credenciais, configurações pessoais, código/logs privados ou resultados de clientes.
- Fixtures e exemplos devem ser públicos ou sintéticos. Resultados reais pertencem ao projeto/registro autorizado.
- Não habilite captura de memória nem altere projetos consumidores como efeito de instalar este pacote.
- Ferramentas não concedem autorização para merge, deploy, publicação ou envio de dados.
- Uma checagem offline comprova compatibilidade limitada, não acurácia Jev nem economia Codex.

- Em 02/10/2026 Gabriel autorizou publicar cada nova integração de ferramenta na main remota após os checks obrigatórios. Branch/PR são preparação, não conclusão. Verifique head/base/CI e confirme origin/main; não force push nem inclua alterações alheias. Essa autorização não concede deploy/produção ou operações nos projetos consumidores.
