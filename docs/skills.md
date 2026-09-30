# Integração com my-skills

Os procedimentos permanecem em my-skills. Este repositório fornece executáveis.
A integração opcional cabe nas skills de descoberta de código: auditoria de
issue, execução de resolução, mapa e investigação de arquitetura. Não é
necessário alterar procedimentos sem essa necessidade. A orientação é:

> Quando nomes/termos exatos não forem conhecidos, consulte `my-tools status`.
> Se search estiver habilitado, permitir envio e possuir globs autorizados salvos, use
> `my-tools search "comportamento procurado" --top 5 --json --stats`.
> O launcher aplica os caminhos/extensões do escopo salvo. Confira os arquivos
> retornados. Se a ferramenta falhar ou os trechos forem insuficientes, use rg e
> leitura direta. Preserve evidência necessária e regras do projeto.

Não é necessário criar uma skill para cada comando nem registrar outro MCP
para usar a primeira versão. O agente precisa alcançar o launcher pelo shell
e acessar a credencial pelo ambiente autorizado ou cadastro pessoal do launcher. Teste descoberta em uma sessão
nova do runtime escolhido. Disponibilidade em CLI local não comprova Cloud.

Este pacote não edita skills nem ativa consumidores automaticamente. A integração
precisa estar na fonte canônica do my-skills, com configuração local explícita por
consumidor. Links existentes acompanham a edição. Valide uma chamada real em
conversa nova; isso comprova disponibilidade, sem prometer seleção em todo pedido.

Veja o [fluxo proporcional de busca](search-workflow.md) para decisão entre
rg/Siftr, leitura de chamadores, fallback e interpretação das métricas.
