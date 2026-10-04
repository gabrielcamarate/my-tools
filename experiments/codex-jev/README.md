# Codex Jev: laboratório isolado

Experimento de substituição da compactação, não uma ferramenta ativada nas sessões normais.
Fonte fixada em `manifest.json`; patch de transporte OpenRouter em `openrouter.patch`.
O engine e as decisões de seleção permanecem upstream. Requisições têm timeout de 10 segundos.

## Limites de isolamento

- Não substituir `codex`, registrar hooks/MCP nem alterar `~/.codex`.
- Usar um `CODEX_HOME` próprio para cada braço da comparação, sem links para sessões/configuração pessoal.
- Credencial OpenRouter resolvida do processo ou do arquivo pessoal privado já usado pelo Siftr, sem duplicação.
- Somente fixtures e tarefas sintéticas podem entrar no laboratório.
- O Desktop principal e suas threads continuam usando o engine instalado.
- O launcher Desktop upstream não faz parte deste teste: seu caminho depende da versão embutida no aplicativo.

## Teste do helper

Depois de preparar a fonte e Bun em runtime separado:

```bash
python3 experiments/codex-jev/test_helper.py --source /caminho/codex-jev-lab
python3 experiments/codex-jev/test_helper.py --source /caminho/codex-jev-lab --live
python3 experiments/codex-jev/test_helper.py --source /caminho/codex-jev-lab --live --recoverable
```

Sem `--live`, uma chave explicitamente vazia deve rejeitar a poda e permitir fallback.
Com `--live`, 24 resultados obsoletos competem com uma regra necessária sem outra fonte.
O controle `--recoverable` permite reler a regra e não exige retenção daquele resultado.
Redução do JSON do helper não comprova economia total nem continuidade do agente.

Validação do motor concluída no laboratório. Resultados, decisão e limites em [REPORT.md](REPORT.md). Não ativar no Codex principal.

## Teste do motor

O teste `test_engine.py` usa o app-server do fork, uma sessão própria e um backend
ChatGPT sintético em loopback. Verifica substituição, fallback e o contexto recebido
pela continuação. Não mede qualidade ou latência real do serviço ChatGPT.

```bash
python3 experiments/codex-jev/test_engine.py --source /caminho/codex-jev-lab --mode baseline
python3 experiments/codex-jev/test_engine.py --source /caminho/codex-jev-lab --mode jev
python3 experiments/codex-jev/test_engine.py --source /caminho/codex-jev-lab --mode missing-key
```

`--chatgpt` executa a comparação real com tarefa sintética. A API do app-server
recebe em memória somente um access token/account existente, sem refresh token.
A autenticação original nunca é regravada nem usada para renovar o token.
Se o token não estiver disponível ou válido, o teste termina; não solicita refresh
nem altera o login original. O resultado precisa comprovar a continuidade e qual
caminho de compactação foi aceito. O `CODEX_HOME` temporário é removido no fim.

O launcher `run.py` recusa HOME/CODEX_HOME pessoal, diretório não vazio de terceiros
e symlinks nos caminhos de controle. `baseline` e `jev` usam o mesmo binário do
fork: a comparação não mistura versões diferentes do Codex.

## Preparação reproduzível

Escolha uma pasta **nova**, separada de instalações existentes. Exemplo para Linux
x86_64, com Git, npm e um toolchain Rust compatível já disponíveis:

```bash
git clone https://github.com/AyushChauhan9389/codex-jev.git /caminho/codex-jev-lab
git -C /caminho/codex-jev-lab checkout --detach eed01388e78d646ea0e2bc694270820a09673ce5
git -C /caminho/codex-jev-lab apply /caminho/my-tools/experiments/codex-jev/openrouter.patch
# Se usar Rust 1.98, aplicar também o ajuste de limite do compilador:
git -C /caminho/codex-jev-lab apply /caminho/my-tools/experiments/codex-jev/rust-1.98-build.patch
npm install --prefix /caminho/codex-jev-lab/lab-runtime --ignore-scripts bun@1.4.2
# Usar cargo/rustc por caminho explícito, sem mudar o toolchain global.
# Limitar jobs e destinar os artefatos somente ao laboratório:
cd /caminho/codex-jev-lab/codex-rs
CARGO_BUILD_JOBS=2 CARGO_TARGET_DIR=/caminho/codex-jev-lab/target cargo build --locked --release -p codex-cli --bin codex
```

O helper usa o binário Bun do pacote opcional `@oven/bun-linux-x64`, dispensando
postinstall. Não rode o launcher `.desktop` upstream durante esta avaliação.
O Rust usado no laboratório está registrado no manifesto; o upstream pede 1.95.0.
Uma atualização exige revisão de fonte, lockfile, patch e compatibilidade de motor,
seguida dos mesmos testes. Falha deixa o Codex instalado intocado. Para desativar
a experiência basta encerrar o processo separado; não há configuração global a reverter.

O patch de transporte também rejeita probabilidades fora de [0, 1]. O patch de
compilação aumenta somente `recursion_limit` do crate `codex-chatgpt`, conforme
o diagnóstico do Rust 1.98; não altera algoritmos, tipos ou chamadas de rede.
