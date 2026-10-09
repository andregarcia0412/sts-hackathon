# Handbook — Incerteza tecnológica (INC)

No início não dava para saber se o objetivo seria alcançado, nem como; a linha entre P&D e engenharia é o risco
tecnológico (Frascati 2015 §2.18; Guia MCTI 2020 §6.3).

## Armadilhas

- **INC-D4**: só falha EXPERIMENTAL conta (hipótese refutada, comparador que falhou no ensaio). "v1 falhou e v2
  corrigiu por configuração" não prova incerteza: é exatamente o padrão dos projetos de rotina.
- **INC-D9**: falha OPERACIONAL (parâmetro, permissão, cadastro, receita do fornecedor) conta contra: é rotina.
- **INC-D2**: pergunta que já nomeia a solução ("como aplicar a técnica conhecida", "como integrar ao produto
  contratado") é rotina; pergunta técnica aberta ("é possível associar sem depender de...?") é a que sustenta.
- **INC-W1/W2**: a busca é pela solução da barreira, não pelo produto. Se a solução já estava acessível a um
  profissional competente, não havia incerteza.
- **INC-D12**: "investigada" exige a hipótese executada contra comparadores, com registro por versão nas medições.
  Só plano, diagrama ou memorando leva a ALEGADA, NÃO VERIFICÁVEL.
- **INC-D1**: risco de mercado, prazo, orçamento ou política não é incerteza tecnológica.

## Quando usar cada estado

- **INVESTIGADA** (P&D): a solução não estava acessível, e a hipótese foi executada e confrontada com comparadores,
  com medições por versão (inclusive quando falhou).
- **NÃO CARACTERIZADA** (rotina): a solução já estava acessível, ou as falhas foram operacionais e se resolveram por
  configuração.
- **ALEGADA, NÃO VERIFICÁVEL** (insuficiente): use SOMENTE quando não há registro da execução da hipótese (plano,
  diagrama, memorando sem IDs). Se há ensaio registrado contra comparadores, escolha entre INVESTIGADA e NÃO
  CARACTERIZADA.

## Sinais que não contam

`natureza_informada_pela_equipe`; ter falhas registradas (rotina também tem); número de testes; depoimento da
entrevista (divergências mudam a justificativa, não o estado).
