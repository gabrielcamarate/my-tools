# Avaliação isolada Codex Jev, 2026-10-04

Decisão: manter como **laboratório experimental**, sem ativação no Codex principal.
Fonte: [AyushChauhan9389/codex-jev](https://github.com/AyushChauhan9389/codex-jev),
revisão e patches fixados no manifesto. O fork tinha 0 estrelas e 0 forks na consulta
GitHub desta data; popularidade e maturidade não estão demonstradas.

## Resultados

| Verificação | Resultado |
|---|---|
| Build separado | CLI 0.159.0 compilado; SHA256 no manifesto |
| Upstream formatter e teste Rust do ajuste de build | `just fmt` passou; `just test -p codex-chatgpt --release`: 7 passaram, 0 ignorados |
| My Tools / My Skills | 95 e 13 testes passaram; 23 skills validadas |
| Mesmo motor, backend sintético | Nativa, Jev e fallback sem chave passaram |
| ChatGPT real, gpt-6-sol, esforço baixo | 3 execuções por braço; todos preservaram regra e limite |
| Compactação nativa | 8,069 / 8,091 / 12,437 s; mediana 8.091 s |
| Compactação Jev | 1,379 / 1,554 / 1,388 s; mediana 1.388 s |
| Diferença de medianas | 82.8% menos espera neste teste |
| Fallback real sem chave | 7,689 s; compactação nativa e continuação corretas |
| Provedor offline | Falha de rede, JSON inválido, HTTP 401, probabilidade inválida e redução insuficiente rejeitados; seleção válida aceita |
| Isolamento | Launcher recusa HOME pessoal, diretório não pertencente ao laboratório e symlinks de controle |

O registro da sessão confirmou ausência de `compaction_response_id` nos três braços
Jev e presença nos braços nativos e no fallback. Isso comprova substituição no
motor separado, não somente funcionamento de um subprocesso auxiliar.
A continuação respondeu `ROUNDING=half-up; LIMIT=125`, usando evidência preservada.
A fonte dessa regra estava declarada apagada, impedindo uma releitura como atalho.

O helper reduziu um JSON sintético de 584.200 para 3.550 caracteres, preservando
pares de chamadas e resultado indispensável em três execuções reais. Isso é tamanho
de fixture, **não medição dos tokens faturados, da cota Codex ou do contexto inteiro**.
O cenário do motor usa resultados menores para limitar o custo do teste real.

## Limites e riscos

- Apenas um comportamento sintético foi repetido. Não comprova tarefas longas,
  histórico multimodal, todas as interfaces de ferramentas ou recuperação após crash.
- Quando a fonte pode ser relida, o helper pode descartar seu resultado antigo:
  o controle recuperável demonstrou esse comportamento. Isso pode gerar retrabalho.
- A seleção é lossy e pode errar. Validação de pares e fallback não detectam toda
  perda semântica. O usuário e os itens recentes são preservados pelo helper.
- O fork usa Codex 0.159.0; o instalado é 0.160.0. Não substituir o motor do Desktop.
- O patch altera transporte/credencial para OpenRouter e valida probabilidades;
  não muda o algoritmo de seleção. Outro patch aumenta somente o limite do compilador
  Rust 1.98.1; o upstream especifica Rust 1.95.0.
- O helper tem timeout por requisição de 10 s; o motor upstream limita o helper a
  120 s antes de fallback. Uma indisponibilidade ainda pode acrescentar espera.
- Não se mediram economia total de tokens nem ganho em uma tarefa real de projeto.
  O resultado atual mede latência real de compactação sobre histórico sintético.

## Segurança e uso

Executável, configuração e AGENTS pessoais permaneceram com os mesmos hashes.
Nenhum hook global, plugin, launcher Desktop, Cloud, serviço ou ambiente de produção
foi alterado. Sessões e servidores de teste temporários foram encerrados/removidos.
A credencial OpenRouter foi resolvida pela rota pessoal nativa, sem ser copiada
para o repositório. O teste ChatGPT usou somente access token/account em memória,
sem refresh token ou alteração do login pessoal.

Comandos reproduzíveis, instalação e limites estão no [README](README.md).
Resultados estruturados em `results/`; o experimento fica fora de `tools.json`
e dos comandos normais de instalação/atualização. Atualizações exigem nova revisão
contra a versão oficial e repetição dos testes pertinentes.

Este laboratório **não acelera a compactação desta conversa ou de novas conversas
normais do Desktop**. Isso exigiria mudar o motor usado pelo aplicativo e uma
validação própria de compatibilidade, fora da autorização atual.
