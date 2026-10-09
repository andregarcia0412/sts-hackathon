# PRJ02 — Método e referência

Documento sintético. Data de corte: 2025-05-12.

## 1. Referência anterior

Igualdade textual, faixa de valor/tempo e atribuição bipartida de custo mínimo já eram dominadas. A última força pareamento em componentes ambíguos quando dois relógios divergem; não representa causalidade relativa nem abstenção por margem.

Os catálogos/manuais citados neste documento são extratos fictícios definidos acima; não são documentos internos de instituição real. O trecho fornecido descreve as funções relevantes à comparação.

## 2. Mecanismo e hipótese

Grafo de candidatos com arestas apenas para mesmo valor e janela corrigida de 120 s. Estimar deslocamento pela mediana dos pares-âncora inequívocos. Custo de aresta: 0,6×|diferença temporal corrigida|/120 + 0,4×(1-Jaccard dos tokens da descrição em minúsculas). Impor ordem relativa somente dentro de cadeia com sequência confiável, nunca entre contas independentes. Resolver custo mínimo; abster se a margem entre as duas melhores atribuições for menor que 0,15. Bipartido usa o mesmo custo, sem restrição de ordem ou abstenção.

## 3. Protocolo e critérios

1.200 pares, 400 em cada deslocamento de relógio de 0, +90 e -90 segundos; 60 ambíguos por perfil, total 180. Mesma referência lacrada para quatro alternativas. Limites definidos antes da rodada: pelo menos 95% de acerto e no máximo 1% de vínculos falsos. Os 48 pares recusados pelo grafo pertencem ao estrato ambíguo.

## 4. Parâmetros, versões e execução registrada

- semente: 202502
- janela_s: 120
- margem_abstencao: 0.15
- perfis_desvio_s: [0, 90, -90]

Versões localizadas: texto-v1, faixa-v2, bipartido-v3, restrito-v4. Configuração estruturada: `configuracao.json`. Datas e estados: `cronologia.csv`.

## 5. Leitura e reconstrução dos resultados

`medicoes.csv` é a fonte dos contadores por cenário e das medições numéricas entregues. `resultados.csv` é calculado a partir dela, não é uma segunda confirmação independente. Para contadores, somar numeradores e denominadores apenas dentro de um ensaio. Ensaios diferentes podem compartilhar a população. Em resultados.csv, base_de_calculo preserva o total de referência e descricao_base explica o que ele representa. Para média, mediana e diferença entre maior e menor valor, usar a operação indicada. Para percentil_95 de histograma, ordenar valores e localizar o posto teto(0,95 × soma dos pesos). valor_observado reproduz uma medição única. indicador_precalculado transcreve um indicador já calculado: conferir essa transcrição não reproduz seu cálculo original. O LEIA_ME contém o dicionário completo.

Os arquivos não contêm transações bancárias nem uma implementação completa do sistema descrito. São registros primários fictícios do exercício. `entradas.csv` e `observacoes.csv` contêm recortes explicitamente identificados; não pretendem conter todas as entradas da população de um contador. A semente, quando informada, identifica o desenho sintético do cenário, não um executável ausente.

## 6. Limite da conclusão

Conclusão limitada à associação com sequência confiável e aos três deslocamentos ensaiados. Sem inferência sobre transações reais ou ausência de ordem de origem.

## 7. Continuidade e detalhamento técnico

Executar a separação de cadeias sem sequência confiável e comparar a margem de abstenção com os deslocamentos de relógio já ensaiados.

As especificações descrevem o recorte sintético e não equivalem a um programa executável de produção.

```text
ancoras = pares_com_candidato_unico(mesmo_valor)
desvio = mediana(hora_extrato - hora_razao das ancoras)
para cada componente:
  candidatos = arestas_mesmo_valor_e_janela(120s, desvio)
  remover_atribuicoes_que_invertem_sequencia_confiavel()
  melhor, segunda = duas_melhores_atribuicoes_por_custo()
  se custo(segunda)-custo(melhor) < 0.15: devolver_revisao()
  senao: emitir(melhor)
```


