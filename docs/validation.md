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
