# Proveniência

O controlador, comparador, fixtures e testes deste repositório são próprios.
O padrão de fonte canônica com launcher/link pessoal se inspira no projeto
[gabrielcamarate/my-skills](https://github.com/gabrielcamarate/my-skills).

Siftr é de [Bentlybro](https://github.com/Bentlybro/siftr), licença MIT. A revisão
integrada inicialmente é `4984c23dd338596a2ec62d836f742d98e7bb4722`.
O código upstream é obtido durante instalação e fica no armazenamento local,
sem cópia ou atribuição de autoria ao controlador. Seu LICENSE permanece na fonte.

A interface do agente é a CLI/MCP oficial gerada pelo uv, sem alteração da fonte upstream. O controlador gerencia origem e revisões; não é um serviço do fornecedor nem promessa de suporte oficial.

TypeSafe/Jev e OpenRouter são provedores externos. Este repositório não redistribui
modelos e não contém credenciais, resultados privados ou garantia de benefício.

Jev Pruner é de [tamaratran](https://github.com/tamaratran/jev-pruner), MIT. Revisão integrada `edbc60262a5edc07e18d646c1a3f8a9f0ae868c5`. Fonte, licença, plugin, skill e wrapper permanecem upstream no armazenamento local. My-tools compila e gerencia as revisões, sem redistribuir cópia do engine neste repositório.

O ajuste de provedor do Pruner, autorizado em 30/09/2026, é mantido em `patches/jev-pruner-openrouter.patch`: URL/modelo, leitura da chave OpenRouter, orientação da skill e testes de integração. Não é uma release upstream nem promessa de suporte do autor; o LICENSE MIT e a autoria dos trechos permanecem do upstream. O motor de poda não foi adaptado.

Canny é de [qkal](https://github.com/qkal/Canny), MIT, revisão `f2c5e53779445d60dc4a09d2dbced2308fccb820`, versão 0.3.0. Fonte/CLI/hooks/licença permanecem upstream no armazenamento local. O patch autorizado `patches/canny-openrouter.patch` adapta URL/modelo/credencial, isola cache por endpoint e atualiza ajuda/testes. Não altera checks, eventos, regras, ledger, install ou decisões do hook. O engine não é redistribuído neste repositório.

Jeval é de [rlaope](https://github.com/rlaope/jeval), Apache-2.0, revisão `61bdcccf9038ff898e82f9465d1a979f5d68bc6e`, versão 0.2.0. Fonte, licença e seis skills permanecem upstream no armazenamento local. Não há patch de provedor: o avaliador é offline. Fixtures/resultados aqui são sintéticos, sem dados de projetos consumidores.
