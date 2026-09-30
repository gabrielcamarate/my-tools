# Arquitetura

## Fluxo

```text
skill ou usuário
    -> launcher my-tools
    -> configuração da raiz do projeto
    -> capacidade e provider habilitados
    -> versão aceita (ou pin)
    -> adaptador
    -> runtime isolado
    -> stdout/stderr e exit code originais
```

O launcher resolve o checkout canônico mesmo por symlink. O controlador não usa
shell para montar chamadas. O armazenamento contém `state.json` e
`tools/<nome>/<sha>/`; cada runtime tem fonte Git, venv sem dependências externas,
runner e registro de origem/hash. Essa estratégia é específica do Siftr atual,
cujo `pyproject.toml` não declara dependências. Uma mudança nisso exige revisão
do adaptador, em vez de instalar dependências arbitrárias automaticamente.

O venv é executado pelo caminho direto do Python, sem depender de scripts de
ativação que apontem para o diretório staging anterior. A preparação é verificada
novamente depois da mudança de diretório. Alterações no estado usam replace
atômico e lock POSIX não bloqueante para mutações concorrentes.

`approved` na configuração significa a revisão **ativa aceita localmente**, não
qualidade Jev comprovada. Aceitação de atualização e adoção no workflow são
decisões distintas. `experimental` no catálogo registra essa diferença.

## Acrescentar uma ferramenta

1. Identificar uma tarefa, baseline e critério de aceite.
2. Registrar fonte HTTPS pública, licença, SHA revisado, capacidade e credenciais
   por nome de variável, nunca por valor.
3. Implementar um módulo em `src/my_tools/` com `prepare` e `check`; registrar
   explicitamente em `adapters.py`. O catálogo não importa módulos arbitrários.
4. Estender a validação do catálogo/configuração e o comando da capacidade.
5. Testar instalações isoladas, falhas antes da ativação, rollback e pins.
6. Documentar envio de dados, contratos, fallback e matriz de compatibilidade.
7. Executar o piloto; manter experimental ou aprovar para um uso delimitado.

O catálogo expõe apenas ferramentas efetivamente integradas. Não contém nomes
de candidatos como se estivessem implementados. Os perfis são configuração
portável sem caminhos pessoais ou segredos. As regras dos projetos prevalecem.

## Limites

- Instalação por Git exige rede; inferência exige rede e credencial própria.
- Isolamento de venv não é isolamento de rede, filesystem ou permissões.
- Hashes detectam alteração acidental da instalação; não são defesa contra um
  invasor com controle da conta e do registro de hashes.
- Falha de processo/compatibilidade deixa o ativo intacto. Falha de máquina/disco
  durante persistência ainda requer reconciliação do estado.
- Não há coleta automática de runtimes antigos ou registro global de todos os
  projetos consumidores. Isso evita eliminar versões ainda fixadas em projetos.
