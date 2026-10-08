# Codex Jev local, 08/10/2026

## Mudança

Motores opt-in correspondentes ao CLI e ao Desktop instalados, perfis separados,
helpers imutáveis por runtime e atualização via hook pessoal do Omarchy.
Pacotes novos incompatíveis mantêm o motor oficial atual disponível. API de
compactação desconhecida é recusada antes de compilar. Mudança só no renderer
revalida o bundle, aproveitando o motor idêntico já aceito.

## Evidências verificadas

- Controlador: 122 testes Python locais aprovados.
- CLI 0.162.0: três testes Rust de produção, igualdade de schemas com o pacote,
  seis contratos do provedor, proteção contra dotenv/preload com controle positivo,
  Code Mode real e compactação/continuação nos três modos de backend sintético.
- CLI instalado: codex-jev --version retornou 0.162.0.
- Helper real: fixture pública sintética de 59 itens, 584200 caracteres para 3550,
  em 0,79 s. Regra necessária preservada e pares íntegros. Uma requisição Jev.
- Unidade transitória systemd: confirmou acesso a codex/mise no ambiente do usuário.
- Desktop 0.162.0-alpha.2: três testes Rust aprovados e aceitação offline completa.
- Janela nativa aberta: App Server usando executável alpha modificado, helper Jev
  e perfil Electron/CODEX_HOME próprios. Processos originais preservados.
- Hook Omarchy executado: ambos atuais, sem recompilação, 1,689 s e pico de 56,1 MiB.
- Primeiro login e compactação autenticada na interface: ainda pendentes.

## Limites

A fixture não demonstra economia total de tokens, quota ou duração de issues.
A prova sintética do motor não é uma prova de qualidade do modelo ChatGPT.
O primeiro login e a primeira jornada autenticada do Desktop ficam separados.
Conversas abertas preservam seu motor; a atualização vale ao reabrir o perfil.
O perfil Jev destina-se a histórico técnico elegível para o provedor externo.

## Ferramentas e dispensas

Jev: helper upstream usado com contratos sintéticos e uma fixture real elegível.
AI-Memory: consulta histórica local com escopo explícito; nenhuma escrita/captura alterada.
Pruner: dispensado porque o histórico desta sessão inclui material privado excluído.
Siftr: dispensado para caminhos/símbolos conhecidos e inspeção do bundle instalado.
Test Filter: dispensado para gates finais e suites focadas rápidas.
Browser: sem interface web sob teste; a integração alvo é o app nativo.
Omarchy: skill/hook nativo pessoal usados, sem alterar arquivos empacotados.
