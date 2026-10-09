# PRJ15 — Método e referência

Documento sintético. Data de corte: 2025-07-28.

## 1. Referência anterior

Texto padrão e lista dos maiores fatores explicavam valores presentes ao final da análise, que podiam diferir dos usados na decisão após enriquecimento tardio.

Os catálogos/manuais citados neste documento são extratos fictícios definidos acima; não são documentos internos de instituição real. O trecho fornecido descreve as funções relevantes à comparação.

## 2. Mecanismo e hipótese

Capturar snapshot de versão e fatos efetivamente consumidos em cada regra. Construir explicação apenas das dependências que contribuíram ao caminho escolhido, com referência ao snapshot, nunca ao cadastro mais recente. Ao reavaliar, abrir nova trilha com parent_id da anterior. Confrontar cada explicação com replay da mesma versão do motor.

## 3. Protocolo e critérios

80 alertas; versões rastro-v1 e rastro-v2 confrontadas com replay. Dois enriquecimentos tardios divergiram em rastro-v1; em rastro-v2 os 80 correspondem. Vinte analistas sintéticos A01–A20: cada um lê quatro alertas por método; permutação de ordem contrabalançada consta na configuração e nos registros de leitura. Medianas de 80 tempos por método: 6,4 e 4,1 minutos.

## 4. Parâmetros, versões e execução registrada

- semente: 202515
- analistas_sinteticos: 20
- alertas_por_analista_por_metodo: 4
- ordem: "A01–A10: texto depois rastro; A11–A20: rastro depois texto; alerta=(analista-1)*4+posição"

Versões localizadas: rastro-v1, rastro-v2, texto-v3. Configuração estruturada: `configuracao.json`. Datas e estados: `cronologia.csv`.

## 5. Leitura e reconstrução dos resultados

`medicoes.csv` é a fonte dos contadores por cenário e das medições numéricas entregues. `resultados.csv` é calculado a partir dela, não é uma segunda confirmação independente. Para contadores, somar numeradores e denominadores apenas dentro de um ensaio. Ensaios diferentes podem compartilhar a população. Em resultados.csv, base_de_calculo preserva o total de referência e descricao_base explica o que ele representa. Para média, mediana e diferença entre maior e menor valor, usar a operação indicada. Para percentil_95 de histograma, ordenar valores e localizar o posto teto(0,95 × soma dos pesos). valor_observado reproduz uma medição única. indicador_precalculado transcreve um indicador já calculado: conferir essa transcrição não reproduz seu cálculo original. O LEIA_ME contém o dicionário completo.

Os arquivos não contêm transações bancárias nem uma implementação completa do sistema descrito. São registros primários fictícios do exercício. `entradas.csv` e `observacoes.csv` contêm recortes explicitamente identificados; não pretendem conter todas as entradas da população de um contador. A semente, quando informada, identifica o desenho sintético do cenário, não um executável ausente.

## 6. Limite da conclusão

O resultado mede fidelidade ao cálculo e tempo de revisão, não qualidade do juízo de crédito ou consenso entre analistas reais.

## 7. Continuidade e detalhamento técnico

Executar a comparação de rastros após nova alteração cadastral, mantendo o snapshot da época e o replay como referência de fidelidade.

As especificações descrevem o recorte sintético e não equivalem a um programa executável de produção.

```text
ao avaliar regra:
  fatos_usados = snapshot_da_epoca_da_decisao()
  registrar(regra_id, fatos_usados, dependencias_consumidas)
ao explicar:
  percorrer_apenas_dependencias_do_caminho_decisorio()
  nunca_substituir_fato_por_cadastro_atual()
se reavaliar: criar_nova_trilha(parent_id=decisao_anterior)
```


