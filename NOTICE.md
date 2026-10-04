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

Jeval é de [rlaope](https://github.com/rlaope/jeval), Apache-2.0, revisão `61bdcccf9038ff898e82f9465d1a979f5d68bc6e`, versão 0.2.0. Fonte, licença e seis skills permanecem upstream no armazenamento local. Não há patch de provedor: o avaliador é offline. Fixtures/resultados aqui são sintéticos, sem dados de projetos consumidores.


jev-calibrate: https://github.com/smkrv/jev-calibrate.git, licença MIT, revisão `28bc62065b95eb67709e669a0683e9a5f04f9414`. Patch documentado em `patches/jev-calibrate-openrouter.patch`; fonte/skills/licença permanecem upstream no armazenamento local.

jev-axi: https://github.com/shiftynick/jev-axi.git, licença MIT, revisão `044fae73a05d5699c4b5c47073f1ffc29d9aa82d`. Patch documentado em `patches/jev-axi-openrouter.patch`; fonte/skills/licença permanecem upstream no armazenamento local.

jev-recipes: https://github.com/agencyenterprise/jev-recipes.git, licença MIT, revisão `53e1743e4702b0e7c4aafc5ceb00c006a69327b1`. Patch documentado em `patches/jev-recipes-openrouter.patch`; fonte/skills/licença permanecem upstream no armazenamento local.

tocsin: https://github.com/TPAteeq/tocsin.git, licença MIT, revisão `6be5828b7020b900f4e95cdac6c447cddb8b750c`. Patch documentado em `patches/tocsin-openrouter.patch`; fonte/skills/licença permanecem upstream no armazenamento local.

docjev: https://github.com/jerryjliu/docjev.git, licença Apache-2.0, revisão `c7abe276a970605feb9cb8b27513365b6c10726e`. Patch documentado em `patches/docjev-openrouter.patch`; fonte/skills/licença permanecem upstream no armazenamento local.

jev-spec: https://github.com/nozomi-koborinai/jev-spec.git, licença MIT, revisão `f5868225fde330ec068378edb273d77015da847e`. Patch documentado em `patches/jev-spec-openrouter.patch`; fonte/skills/licença permanecem upstream no armazenamento local.

jev-oas-sentinel: https://github.com/ShuhanSun/jev-oas-sentinel.git, licença Apache-2.0, revisão `fae78bcd9fa84e17d4c26b93809f7ce23056828a`. Patch documentado em `patches/jev-oas-sentinel-openrouter.patch`; fonte/skills/licença permanecem upstream no armazenamento local.

hunch: https://github.com/Kelbie/hunch.git, licença MIT, revisão `c2c680ed2c12c42c8a1b668a4b0b0858c5f463a6`. Patch documentado em `patches/hunch-openrouter.patch`; fonte/skills/licença permanecem upstream no armazenamento local.

snifftest: https://github.com/DanRWilloughby/snifftest.git, licença MIT, revisão `240653e2b082c114c38fed50a42e7eb311e21219`. Patch documentado em `patches/snifftest-openrouter.patch`; fonte/skills/licença permanecem upstream no armazenamento local.

semdecide: https://github.com/sharziki/semdecide.git, licença MIT, revisão `33cf5c03c50e02e59df3f3ea81f0650f6b791545`. Patch documentado em `patches/semdecide-openrouter.patch`; fonte/skills/licença permanecem upstream no armazenamento local.

## Optional Codex Jev lab

The isolated compaction experiment references AyushChauhan9389/codex-jev at
`eed01388e78d646ea0e2bc694270820a09673ce5` (Apache-2.0), based on OpenAI Codex
rust-v0.159.0. Its vendored fast-jev-compaction helper retains the MIT license.
My Tools stores only provider/build patches, launch safeguards and synthetic
acceptance tests; upstream source and binaries are obtained separately.
