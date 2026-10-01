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

Antes da ativação, o instalador verifica a fonte recebida, origem registrada,
ausência de novas dependências, interface CLI e testes upstream com credenciais
retiradas do ambiente. Uma alteração desconhecida pode exigir atualização do
instalador. Testes passando não certificam acurácia de decisões nem ganho de tokens.

Somente revisões previamente aceitas podem ser resolvidas para uso. Preparação de candidato não ativa seu entrypoint. Instalação repetida preserva a versão aceita; atualização não desfaz uma aceitação explícita só porque o catálogo ainda aponta para a baseline anterior.

Exit codes: 0 concluído; 1 falha em instalação/lote/doctor; 2 configuração inválida
ou candidato pendente; 130 interrupção.
Em lote, uma falha tem precedência sobre pendências no exit code; o JSON registra
o resultado individual de todas as ferramentas. Não há atualização em background.

O controlador é atualizado pelo Git separado dos programas externos. O catálogo
revisado pertence a commits públicos deste repositório. Não modifique runtimes
instalados diretamente: isso invalida a verificação de integridade.

## Entrypoints oficiais

Depois de `integrate siftr --apply`, update/rollback também prepara e verifica o MCP oficial e troca o symlink estável. O registro do cliente precisa apontar para esse symlink; reinicie processos existentes para carregar a nova versão. Runtimes anteriores são preservados.

O MCP usa a versão do executável registrado no cliente. Compatibilidade offline não comprova qualidade do pacote.

O estado principal, registro nativo e symlink são arquivos distintos. A restauração após falha de persistência é compensatória: falhas múltiplas/quedas podem deixar divergência. `my-tools doctor` identifica divergência e retorna falha; `my-tools integrate siftr --apply` reconcilia com a versão aceita no estado principal. Isso não instala candidato pendente nem apaga runtimes de recuperação.
