# Skills e MCPs oficiais

O agente usa a interface do fornecedor. Para o Siftr, são quatro chamadas MCP: `semantic_search`, `focused_read`, `pick_relevant` e `filter_output` experimental.

O my-tools fornece instalação e controle de versão; o my-skills mantém o procedimento. Quatro skills de descoberta orientam a escolha antes da primeira busca: auditoria de issue, resolução, mapa e arquitetura. Outras skills não são alteradas por hábito.

- Localização confirmada por arquivo/trecho/contexto: leitura direta.
- Símbolo ou mensagem exata: rg.
- Comportamento sem localização confirmada: semantic_search primeiro.
- Arquivo grande e pergunta localizada: focused_read.
- Lista longa de testes/arquivos: pick_relevant, sem dispensar gates.
- Log existente saneado/autorizado: filter_output, experimental.

Ausência/falha/resultado insuficiente: busca local e leitura direta. Confira chamadores e contratos. Sugestão não prova ausência nem implementação ativa. Não repita descoberta com contexto já conhecido.

O MCP oficial precisa estar conectado na sessão, receber a chave pelo setup do Siftr e acessar arquivos autorizados. Não impõe filtros ou isolamento por projeto. Skills orientam escolhas, não impõem isolamento de filesystem nem autorização de envio. Outro ambiente precisa de instalação/configuração próprias.

Teste o caminho real em sessão nova, confira as chamadas e avalie a resposta. Invocação explícita de skill não comprova seleção implícita universal. Compare ganho em tarefas equivalentes; testes de disponibilidade não demonstram economia.

## Jev Pruner

`gabriel-github-resolution`, `gabriel-loop-engineering`, `gabriel-verification-planning` e `gabriel-release-smoke-test` remetem à skill do plugin `jev-pruner` para logs extensos autorizados. A chamada é o wrapper upstream, sem MCP ou alias de operação no My Tools. Não aplicar também filter_output sobre a mesma saída. Seleção por skill não intercepta automaticamente todas as chamadas; histórico, chave, rede e hook são necessários.

## Descoberta das skills no Claude

`my-tools integrate jev-test-filter --apply` e `my-tools integrate jev-browser --apply`
também criam links individuais em `~/.claude/skills` para os links estáveis de
`~/.agents/skills`. A fonte upstream continua única e updates/rollback acompanham
ambos os clientes. Não há cópia de skills nem MCP registrado automaticamente no Claude.
Reaplique integrate nas instalações antigas: o registro antigo é compatível, mas
`doctor` informa `claude_skill_status: not_registered` até essa reconciliação.
Conflitos externos abortam antes de trocar qualquer link; falhas compensam a troca.
Após configurar, uma nova sessão pode ser necessária para atualizar o catálogo.

## Jeval

`integrate jeval --apply` vincula as seis skills upstream, sem copiá-las no my-skills: `jeval-handoff`, `jeval-instrument-service`, `jeval-labels-harvest`, `jeval-calibration-audit`, `jeval-threshold-from-costs`, `jeval-drift-gate`. `gabriel-verification-planning` e `gabriel-loop-engineering` orientam quando medir decisões rotuladas. Não instrumentar serviços, coletar dados ou alterar gates por efeito de instalar a ferramenta. Use a instalação gerenciada existente; não execute o instalador flutuante mencionado pela skill upstream. Skills orientam uso; não garantem seleção automática de toda tarefa.
