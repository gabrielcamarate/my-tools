# Skills e MCPs oficiais

O agente usa a interface do fornecedor. Para o Siftr, são quatro chamadas MCP: `semantic_search`, `focused_read`, `pick_relevant` e `filter_output` experimental. Não execute `my-tools search` para substituir essas operações.

O my-tools fornece instalação e controle de versão; o my-skills mantém o procedimento. Quatro skills de descoberta orientam a escolha antes da primeira busca: auditoria de issue, resolução, mapa e arquitetura. Outras skills não são alteradas por hábito.

- Localização confirmada por arquivo/trecho/contexto: leitura direta.
- Símbolo ou mensagem exata: rg.
- Comportamento sem localização confirmada: semantic_search primeiro.
- Arquivo grande e pergunta localizada: focused_read.
- Lista longa de testes/arquivos: pick_relevant, sem dispensar gates.
- Log existente saneado/autorizado: filter_output, experimental.

Ausência/falha/resultado insuficiente: busca local e leitura direta. Confira chamadores e contratos. Sugestão não prova ausência nem implementação ativa. Não repita descoberta com contexto já conhecido.

O MCP oficial precisa estar conectado na sessão, receber a chave pelo setup do Siftr e acessar arquivos autorizados. Não usa os filtros `.my-tools.json` do proxy legado. Skills orientam escolhas, não impõem isolamento de filesystem nem autorização de envio. Outro ambiente precisa de instalação/configuração próprias.

Teste o caminho real em sessão nova, confira as chamadas e avalie a resposta. Invocação explícita de skill não comprova seleção implícita universal. Compare ganho em tarefas equivalentes; a integração anterior apenas de busca deve permanecer rotulada como tal.
