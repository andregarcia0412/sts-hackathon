# Handbook — Criatividade técnica (CRI)

O projeto parte de conceitos ou hipóteses originais e não óbvios; mudança rotineira de produto ou processo fica de
fora (Frascati 2015 §2.17; Guia MCTI 2020 §6). Método novo para tarefa comum conta.

## Armadilhas

- **CRI-D5**: configurar, ativar, cadastrar, mapear ou ajustar parâmetro dentro da faixa já suportada, sem alterar o
  algoritmo, é rotina. Frases como "nenhum algoritmo foi modificado" ou "faixa já admitida" são o sinal clássico.
- **CRI-D6**: método novo para uma tarefa comum é positivo; não rejeite só porque a tarefa é corriqueira.
- **CRI-D1**: a hipótese precisa estar registrada antes dos testes (confira as datas da cronologia).
- **CRI-D8**: parâmetro-chave `null` na configuração leva a INDETERMINADA, não a NÃO DEMONSTRADA.
- **CRI-D10**: renomear técnica conhecida não conta; combinação original testada conta. Não use o texto da
  referência anterior (§1 do método) como prova de combinação original.
- **CRI-W1**: parte do documento anterior mais próximo achado pela Novidade; derive dele o problema técnico objetivo.
- Uma pergunta registrada que já nomeia a solução conhecida é sinal fraco aqui: decide o mecanismo, não a pergunta.

## Quando usar cada estado

- **DEMONSTRADA NO RECORTE** (P&D): há elemento técnico próprio (combinação original, regra de decisão nova) com a
  hipótese registrada antes dos ensaios e parâmetros-chave preenchidos.
- **NÃO DEMONSTRADA** (rotina): a mudança se resume a configurar ou ajustar dentro do que o produto já suporta, ou o
  "elemento novo" é renomeação de técnica conhecida.
- **INDETERMINADA** (insuficiente): use SOMENTE quando os parâmetros-chave estão nulos ou o mecanismo não está
  descrito. Se o mecanismo e a hipótese estão documentados, escolha entre DEMONSTRADA NO RECORTE e NÃO DEMONSTRADA.

## Sinais que não contam

`natureza_informada_pela_equipe`; número de testes ou taxa de aprovação; título e adjetivo comercial; depoimento da
entrevista; o simples fato de existir uma "próxima ação" (todos os projetos têm).
