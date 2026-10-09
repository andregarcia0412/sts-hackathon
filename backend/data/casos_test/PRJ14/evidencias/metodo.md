# PRJ14 — Método e referência

Documento sintético. Data de corte: 2025-06-23.

## 1. Referência anterior

Pontuação individual e grafo temporal com expiração fixa foram especificados como comparadores. O primeiro ignora vínculos; o segundo apaga a cadeia quando contas alternam destinos perto do fim da janela.

Os catálogos/manuais citados neste documento são extratos fictícios definidos acima; não são documentos internos de instituição real. O trecho fornecido descreve as funções relevantes à comparação.

## 2. Mecanismo e hipótese

Representar aresta por evento e predecessores causais. Manter aresta enquanto houver descendente confirmado dentro do horizonte de 15 minutos, com teto absoluto de 45 minutos. Fechar componente ao perder continuidade causal. Pontuar recorrência de caminho e redistribuição de destinos, sem usar nome da conta como rótulo. Testar se esse ciclo de vida recupera campanhas perdidas pela expiração fixa, sem ultrapassar 25 alertas adicionais por lote.

## 3. Protocolo e critérios

14 campanhas em 120 mil eventos normais. Três alternativas na mesma sequência; verdade de referência antes da comparação. Pontuação individual detecta seis campanhas, temporal nove e causal treze. Os 22 alertas adicionais do causal frente ao individual incluem sete verdadeiros de campanhas distintas recuperadas e 15 falsos.

## 4. Parâmetros, versões e execução registrada

- semente: 202514
- horizonte_min: 15
- teto_min: 45
- capacidade_alertas_adicionais: 25

Versões localizadas: individual-v1, temporal-v2, causal-v3. Configuração estruturada: `configuracao.json`. Datas e estados: `cronologia.csv`.

## 5. Leitura e reconstrução dos resultados

`medicoes.csv` é a fonte dos contadores por cenário e das medições numéricas entregues. `resultados.csv` é calculado a partir dela, não é uma segunda confirmação independente. Para contadores, somar numeradores e denominadores apenas dentro de um ensaio. Ensaios diferentes podem compartilhar a população. Em resultados.csv, base_de_calculo preserva o total de referência e descricao_base explica o que ele representa. Para média, mediana e diferença entre maior e menor valor, usar a operação indicada. Para percentil_95 de histograma, ordenar valores e localizar o posto teto(0,95 × soma dos pesos). valor_observado reproduz uma medição única. indicador_precalculado transcreve um indicador já calculado: conferir essa transcrição não reproduz seu cálculo original. O LEIA_ME contém o dicionário completo.

Os arquivos não contêm transações bancárias nem uma implementação completa do sistema descrito. São registros primários fictícios do exercício. `entradas.csv` e `observacoes.csv` contêm recortes explicitamente identificados; não pretendem conter todas as entradas da população de um contador. A semente, quando informada, identifica o desenho sintético do cenário, não um executável ausente.

## 6. Limite da conclusão

Capacidade de revisão prevista é 25 alertas adicionais por lote. O experimento cobre 14 campanhas, não todo tipo de golpe.

## 7. Continuidade e detalhamento técnico

Executar o exame de campanhas com continuidade causal além das janelas ensaiadas e confrontar os alertas com a capacidade de revisão.

As especificações descrevem o recorte sintético e não equivalem a um programa executável de produção.

```text
para aresta nova:
  ligar_predecessores_causais_confirmados()
  conservar enquanto descendente_ativo_em_15min e idade <= 45min
  expirar quando continuidade_causal termina ou idade > 45min
  pontuar_recorrencia_de_caminho_e_redistribuicao()
  comparar_alerta_com_referencia_lacrada()
```


