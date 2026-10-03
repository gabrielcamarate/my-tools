# Jeval: evidência sintética de adoção

Data local: 02/10/2026; timestamps dos artefatos são UTC (já 03/10). Upstream 0.2.0, SHA `61bdcccf9038ff898e82f9465d1a979f5d68bc6e`, fonte sem patch, Apache-2.0.

| Verificação | Resultado |
|---|---|
| Testes upstream | 647 passaram, 84.81 s |
| OpenRouter real | 1 requisição, 16 exemplos sintéticos; 16/16 classificações corretas |
| Modelo observado | `typesafe/jev-1.13-20260917` |
| Ingestão e rótulos reais sintéticos | Preset oficial `jev-native`, 16 labels gold separados por `request_id` |
| Avaliação dos 16 casos | ECE 0.076, intervalo 95% 0.041–0.132; dados insuficientes para decisão |
| Controle de erros inseridos | 200 gold, 40 erradas, confiança 0.9: acurácia 80%, ECE 0.100 (95% 0.050–0.145) |
| Separação de dados | 1 silver separado, 1 sem rótulo excluído |
| Baseline independente | 160/200 = 0.8; gap absoluto para confiança 0.9 = 0.1 |
| Custo hipotético erro=20/revisão=1 | Limiar 1.0, auto_rate 0%; exportado, não implantado |
| Descoberta local nativa | App-server `skills/list`: seis skills habilitadas, zero erros |
| HOME temporário | Instalação, integração, demo HTML e skills sem chave passaram; não é teste Cloud |

[Relatório live HTML](live-report.html), [resumo](live-report.md), [controle HTML](control-report.html), [controle Markdown](control-report.md). `decisions.jsonl` contém respostas reais a exemplos sintéticos. `control-decisions.jsonl` tem erros artificialmente inseridos, não respostas de modelo. Nenhum resultado privado foi exportado. As labels gold são respostas determinísticas revisadas destas fixtures, não rótulos de produção.

O teste live demorou 912 ms na chamada API; usage retornou 1199 input_tokens, 308 output_tokens e cost 0.000050358 USD. Isso não mede economia de Codex. Dois reports locais levaram 0.366 s e 0.379 s; sem baseline de tarefa equivalente, não há speedup demonstrado.

Repetir validação offline com a CLI instalada:

```bash
python3 benchmarks/results/jeval-2026-10-02/validate.py
jeval report --root benchmarks/results/jeval-2026-10-02/live --format md
```

O script usa arquivos públicos, HOME de avaliação temporário, remove chaves do subprocesso e configura proxy indisponível. Não faz requisição de inferência; testa métricas, concordância HTML/Markdown, separação gold, limiar e recusas de bins inválidos/falta de labels. Isso não substitui firewall nem constitui bloqueio global de rede. Não reaproveitar estes casos para afirmar qualidade geral ou escolher políticas de produção.

Recursos temporários dos testes foram removidos. Permanecem instalação/links oficiais e estas fixtures públicas. Nenhum hook, instrumentação, captura ou benchmark automático foi criado; nenhum ambiente Cloud foi editado/publicado nesta integração.
