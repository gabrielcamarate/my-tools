# Codex Jev acompanhando CLI e Desktop

Esta extensão sucede o laboratório 0.159.0. CLI e app oficiais continuam sob o
gestor do sistema. O Jev é um patch opt-in sobre a tag OpenAI correspondente a
cada executável instalado, nunca uma substituição do pacote do Omarchy.

## Instalação e uso

```bash
python3 experiments/codex-jev/install.py           # prévia
python3 experiments/codex-jev/install.py --apply
python3 experiments/codex-jev/manage.py status
python3 experiments/codex-jev/manage.py update
codex-jev
chatgpt-jev
```

`codex-jev` e a entrada **ChatGPT (Jev)** usam perfis próprios. O Desktop separa
CODEX_HOME e os dados Electron; o original e suas tarefas não são reiniciados.
O primeiro uso precisa de login no perfil experimental. Nenhuma credencial,
sessão, chave de API ou histórico pessoal é copiado pelo instalador. Skills
pessoais acessíveis pelo HOME permanecem pessoais; MCPs/configuração do perfil
original não são clonados automaticamente. Plugins incluídos no app são
resolvidos pelos recursos do próprio pacote.

O helper ignora carregamento automático de `.env`, configuração Bun do projeto
e opções herdadas de preload. Seu cwd é a fonte fixada; a credencial permanece
na resolução nativa compartilhada. O probe real do Bun inclui controle positivo
antes de confirmar que dotenv/preload ficam bloqueados.

Use somente tarefas técnicas autorizadas para envio ao provedor Jev. A seleção
envia conteúdo de histórico ao OpenRouter. Não abra neste perfil credenciais,
dados financeiros/clientes, mensagens pessoais ou logs operacionais privados.
Separar o perfil não é um detector de dados sensíveis e não concede autorização
de envio. O CLI/app oficiais preservam compactação nativa para esses casos.

## Atualizações do Omarchy

O instalador adiciona **um** hook pessoal `post-update.d`, sem editar arquivos de
`/usr/share/omarchy` ou os launchers oficiais. O hook inicia uma unidade transitória
systemd de usuário, com teto de duas CPUs, um job Cargo, prioridade reduzida e
teto de 16 GiB. O update
não espera a compilação, não duplica um job ativo e não reinicia conversas.

```bash
journalctl --user -u codex-jev-update.service
python3 experiments/codex-jev/manage.py status
```

O controlador detecta CLI e Desktop separadamente, pela versão **e pelo hash** do
pacote. A tag é `rust-v<VERSAO>`, inclusive pré-releases. Obtém o helper da revisão
fixada do fork original e aplica o patch OpenRouter revisado. As versões de
pacotes locais no lockfile da release podem precisar normalização de 0.0.0 para
a versão workspace; versões/checksums/dependências externos não são alterados.
Uma atualização apenas do renderer, com motor e auxiliar idênticos, revalida o
bundle e reutiliza o executável aceito, sem recompilar o Codex.

Antes de aceitar um candidato: build locked, testes Rust do módulo, igualdade de
schemas App Server com o pacote instalado, falhas do provedor, substituição Jev,
fallback nativo e continuação em backend sintético. Não há chamada paga nesses
gates automáticos. A prova com provedores reais fica separada e identificada.

Há um único cache de compilação serializado. Os executáveis aceitos são cópias
separadas, preservando processos em andamento. Um ponteiro é gravado por rename
somente após validação e nova leitura do pacote instalado. A aceitação anterior
é registrada para diagnóstico; não é reativada automaticamente após um upgrade.
Cada runtime tem também seu próprio script helper: uma atualização não reescreve
o helper de um processo anterior. App/CLI já abertos seguem com seu motor até
serem encerrados e reabertos; não há troca de executável durante uma conversa.

Se a versão nova não aceitar o patch, o source/tag não existir, um teste falhar ou
houver falta de memória/runtime, o candidato fica inativo. A falha é registrada
localmente, e os launchers abrem o **motor oficial atual com compactação nativa**.
Se o Desktop perder também o mecanismo de perfil separado, o launcher recusa
abrir o piloto, preservando o app principal, em vez de presumir isolamento.
Não há promessa de corrigir automaticamente qualquer mudança semântica upstream.

O build mantém a otimização release, mas desativa LTO no perfil Cargo inteiro
(`--config profile.release.lto=false`). Uma flag apenas no executável final
não basta quando as bibliotecas do cache ainda contêm bitcode LTO. O linker
também descarta debug na cópia executável (`-C link-arg=-Wl,--strip-debug`). Isso evita a otimização global
demorada a cada atualização. Não é um binário oficial OpenAI; os mesmos gates
de protocolo, compactação e continuação continuam obrigatórios. Símbolos de debug
ficam no cache de compilação, fora da cópia usada pelo launcher.

## Desktop

Em 08/10/2026, o bundle instalado tinha seleção de executável por
`CODEX_CLI_PATH` e perfil por `CODEX_ELECTRON_USER_DATA_PATH`. Esses mecanismos
foram identificados no código local; não são uma garantia pública de estabilidade
entre versões. Cada atualização deve manter a validação do encaixe no app.
Schema compatível e smoke do App Server não provam todas as jornadas gráficas,
permissões, integrações remotas ou transferência de tarefas.

O opt-in é reversível: feche apenas o perfil Jev e abra o app oficial. Para
desabilitar atualizações, remova apenas o hook com marcador
`my-tools: codex-jev-managed-v1`. Não remova perfis com trabalho sem reconciliação.
As compilações/sources anteriores não são apagadas à força nem processos mortos.
