> Histórico do launcher de busca do piloto inicial. As skills atuais usam o MCP oficial; veja [skills](skills.md) e o README. A configuração e os filtros deste fluxo não se aplicam ao MCP.

# Busca proporcional no workflow

Siftr ajuda a localizar código. Depois leia a implementação e seus chamadores;
um resultado relevante não prova que o caminho esteja ativo.

## Preparação uma vez por projeto ou cópia autorizada

```bash
my-tools --project /caminho/do/projeto init --profile search-experimental
my-tools --project /caminho/do/projeto enable search --provider siftr --allow-remote --glob 'src/*.ts' --glob 'tests/*.ts'
my-tools --project /caminho/do/projeto status
```

`init` preserva configurações existentes. Credencial e runtime ficam no
armazenamento pessoal, sem cópia por projeto. Para uma revisão fixa, acrescente
`--pin SHA_COMPLETO` no enable. Globs abaixo precisam refletir os dados autorizados.

## Durante uma investigação

Com função, arquivo ou mensagem de erro exata, comece com busca local:

```bash
rg -n 'nomeDaFuncao' src tests
```

Quando não houver nome e a localização exigir explorar muitos arquivos:

```bash
my-tools --project /caminho/do/projeto search \
  'onde tratamos uma tentativa repetida de executar a mesma operação?' \
  --glob 'src/*.ts' --glob 'tests/*.ts' --top 5 --json --stats
```

Os padrões salvos são usados mesmo sem `--glob` na busca. Uma busca pode selecionar
apenas um subconjunto exato deles, sem ampliar o escopo.

Globs do Siftr usam matching de caminhos; `src/*.ts` inclui .ts aninhados.
Eles não removem dados privados dentro de um arquivo elegível. Em checkouts com
dados misturados, use uma cópia saneada. `--top` limita saída, não todos os arquivos
examinados ou trechos enviados ao provedor.

Leia os trechos devolvidos, confirme o símbolo e procure chamadores quando
a pergunta envolver comportamento do produto:

```bash
sed -n '40,100p' src/arquivo-encontrado.ts
rg -n 'simboloEncontrado' src tests
```

Os caminhos/linhas acima são ilustrativos. Use os realmente retornados e preserve
testes e gates do consumidor. A ferramenta não executa correções nem muda o modelo.

## Fallback e atualização

Sem hits, com `failed_requests` positivo, conteúdo incoerente ou erro, volte a
`rg` e leitura direta. Não repita a mesma busca remota indefinidamente. Scores são
pistas. Função auxiliar sem chamadas pode não ser a implementação ativa.
O adaptador preserva exit codes: nenhum arquivo elegível retorna 1; bloqueio de
configuração do launcher retorna 2. Não há fallback lexical automático.

```bash
my-tools outdated --all
my-tools update --all
my-tools update siftr --accept SHA_COMPLETO_REVISADO
my-tools rollback siftr
```

Repita os casos de qualidade afetados antes de aceitar uma revisão nova.
Compatibilidade offline não substitui o piloto. Resultados privados ficam
no registro autorizado do consumidor.

## Economia e velocidade

A economia aparece quando a pré-seleção reduz leituras e chamadas do Codex até
uma resposta aceita. Pode perder para `rg` em nomes exatos, projetos pequenos
ou investigações com muitos chamadores. Inclua Siftr e fallback no tempo total.

Meça entrada e saída reais do Codex. Cache já está incluído na entrada: não some
novamente. Tokens Jev não são tokens economizados do Codex. Não há conversão
comprovada dessas contagens para cota ChatGPT. Mantenha fonte congelada, pergunta,
modelo, esforço e aceite equivalentes, alterne ordem e inclua falhas. Pré-busca
entregue ao agente mede esse fluxo; não comprova MCP, correções, CI ou produção.
Veja o [protocolo](../benchmarks/protocols/search.md).
