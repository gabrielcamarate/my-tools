# Piloto de busca

## Hipótese

Busca semântica reduz investigação/tokens até uma entrega aceita quando o agente
não conhece o nome do comportamento. Consulta lexical exata continua como controle.

1. Use a fixture pública desta pasta ou revisão congelada de código autorizado.
2. Defina antecipadamente arquivos/trechos essenciais e critério de aceite.
3. Compare fluxo atual (rg + leitura seletiva) e Siftr com o mesmo modelo, esforço,
   escopo, revisão inicial e ferramentas restantes. Alternar ordem entre pares.
4. Comece com três tarefas comparáveis e consultas semânticas/lexicais. Uma amostra
   pequena detecta problemas, mas não comprova ganho geral ou significância.
5. Registre tempo até aceite, tokens medidos, recuperação, erros e intervenções.
   Inclua falhas/bloqueios. Ausência de tokens é null, nunca zero.
6. Revise manualmente omissões: presença no top-k não prova implementação correta.
7. Use compare para síntese descritiva; decida aprovado para uso delimitado,
   experimental, adiado ou rejeitado. Reavalie após mudar ferramenta/modelo/contrato.

## Fixture sintética

Pasta: `benchmarks/fixtures/search-project`. Use a CLI oficial `siftr search` ou a ferramenta MCP `semantic_search`, com caminho explícito para essa fixture. Mantenha o escopo autorizado da sessão.

| Pergunta | Evidência essencial |
|---|---|
| Onde devolvemos créditos quando uma tarefa não termina? | src/credits.py, função refund_failed_job |
| Como identificamos eventos repetidos para evitar cobrança dupla? | src/events.py, função accept_event |
| Qual função interrompe cobranças futuras de uma assinatura? | src/subscriptions.py, função cancel_subscription |

`legacy_billing.py` contém um caminho antigo que não é a implementação ativa.
Esses arquivos não representam produtos/clientes reais. Qualidade da recuperação
é medida separadamente de qualidade da entrega final. Não derive cota ChatGPT de
caracteres cortados ou de tokens Jev.

Copie os JSONs de exemplo para um diretório local ignorado e substitua os valores
por medições com fonte e unidade. Os números de exemplo são fictícios. Preserve
evidência detalhada e orçamento da sessão no registro autorizado do projeto, sem
publicar transcrições, logs privados ou credenciais neste repositório.
