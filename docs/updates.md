# Atualizações

| Operação | Rede | Executa upstream | Ativa versão |
|---|---|---|---|
| outdated | Sim, refs Git públicas | Não | Não |
| update | Sim, se candidato não instalado | Sim, contrato e testes offline | Somente revisão aprovada no catálogo |
| update --accept SHA | Sim, consulta candidato | Sim | Após verificações, a revisão explicitamente aceita |
| rollback | Não | Sim, verificação offline da versão anterior | Versão anterior válida |

Execute `outdated` para identificar a revisão, consulte o diff público entre os
SHAs e só então prepare a candidata. Sem tag estável, cada novo commit da branch
é uma revisão candidata; não existe pressuposto de compatibilidade semântica.
Mesmo patch releases exigem aceitação se o SHA não constar da revisão aprovada.

Antes da ativação, o adaptador verifica a fonte recebida, origem registrada,
ausência de novas dependências, interface CLI e testes upstream com credenciais
retiradas do ambiente. Uma alteração desconhecida pode exigir atualização do
adaptador. Testes passando não certificam acurácia de decisões nem ganho de tokens.

Um pin só aceita revisões previamente ativadas/aceitas. Preparar um candidato
pendente não permite usá-lo indiretamente por pin. Instalação repetida preserva
a versão ativa aceita. `update` também não desfaz uma aceitação explícita apenas
porque o catálogo ainda aponta para a baseline anterior.

Exit codes: 0 concluído; 1 falha em instalação/lote/doctor; 2 configuração inválida
ou candidato pendente; 130 interrupção. Search propaga o código do Siftr.
Em lote, uma falha tem precedência sobre pendências no exit code; o JSON registra
o resultado individual de todas as ferramentas. Não há atualização em background.

O controlador é atualizado pelo Git separado dos programas externos. O catálogo
revisado pertence a commits públicos deste repositório. Não modifique runtimes
instalados diretamente: isso invalida a verificação de integridade.
