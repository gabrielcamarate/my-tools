# Validação da versão inicial

Data: 2026-09-30. Linux, Python 3.14.7.

Resultado local: 29 testes próprios passaram, check público passou, launcher
instalado e Siftr real fixado aprovado pelas verificações offline. O caminho real
de busca na fixture sintética devolveu código 2 por ausência de credencial, como
esperado. Nenhuma inferência foi executada e nenhum ganho de produtividade foi
medido. A configuração da fixture é local/ignorada pelo Git.

## Alegações e evidências

| Alegação | Verificação | Limite |
|---|---|---|
| Candidato com falha não substitui ativo | Testes com Git local, runtime real e CLI incompatível | Não simula perda de disco/máquina |
| Aceitação, rollback e pins preservam revisões | Testes com dois commits e projeto isolado | Somente primeiro adaptador |
| Arquivos de terceiros são preservados | Conflito no launcher e configuração por symlink | Não equivale a segurança contra invasor local |
| Busca exige ativação e permissão de dados | Testes que confirmam ausência de chamada quando bloqueada | Configuração precisa corresponder à autorização real |
| Execução mantém argumentos, JSON e código de saída | CLI sintética e consulta com metacaracteres literais | Acurácia real não é avaliada |
| Falhas e tokens desconhecidos não desaparecem da comparação | Testes do comparador | Estatística descritiva, amostra exploratória |
| Siftr fixado instala e responde ao contrato | Instalação real do SHA do catálogo e suite upstream offline | Sem chamada de inferência, economia ou descoberta desktop/cloud demonstrada |

Comandos reproduzíveis: `python3 -m unittest discover -s tests -v`,
`python3 scripts/check_public.py`, `python3 bin/my-tools install siftr` e
`python3 bin/my-tools doctor`. O CI executa os testes locais e check público em
Python 3.11/3.14. Ele não utiliza credenciais nem reproduz benchmarks live.

Uma nova revisão invalida as verificações afetadas. Upstream, ambiente e resultados
de piloto têm validade própria. Presença de workflow/badge não deve ser descrita
como CI PASS antes do resultado daquele commit.

## Cadastro pessoal de credenciais

Adição posterior: 37 testes próprios passaram, incluindo cadastro persistente
com permissão 600, recusa de symlink/arquivo acessível por outros usuários,
precedência do ambiente e diagnósticos sem valor da chave. O CLI solicita o valor
por prompt oculto em terminal interativo. Esse armazenamento local em texto claro
não é um cofre criptografado e não faz parte do Git.

O primeiro caso de busca live foi executado pelo operador no terminal e retornou
credits.py em primeiro lugar, sem falhas, em aproximadamente 0,94 segundo segundo
a saída fornecida. Isso não mede economia Codex. Os dois casos restantes aguardam
credencial disponível ao executor; não foram reportados como concluídos.

## Integração oficial MCP, 30/09/2026

A integração nativa usa a fonte Siftr aceita sem alterações e o entrypoint gerado pelo uv. Descoberta stdio conferiu os quatro nomes oficiais. Chamadas live de search, read, pick e filter funcionaram com código público e saída sintética. Tempos e respostas reais ficam no registro local autorizado; isso não mede ganho comparável de produtividade.

Testes offline cobrem descoberta MCP real, preservação de comando externo, contrato incompatível, falha de registro, restauração do symlink, rollback e diagnóstico de divergência. Configurações/chaves de clientes não são versionadas. Uma sessão nova precisa validar uso real e política de confirmação no cliente; MCP disponível não garante seleção em toda tarefa. O piloto anterior de busca pelo shell continua histórico, não resultado do pacote completo.
