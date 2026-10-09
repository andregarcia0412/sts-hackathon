# PRJ19 — Método e referência

Documento sintético. Data de corte: 2025-06-09.

## 1. Referência anterior

O produto fictício OCR-5 já oferece correção de inclinação, extração de campos e fila humana abaixo do limiar de confiança. O manual define uso desse limiar.

Os catálogos/manuais citados neste documento são extratos fictícios definidos acima; não são documentos internos de instituição real. O trecho fornecido descreve as funções relevantes à comparação.

## 2. Mecanismo e hipótese

Aplicar OCR contratado, mapear campos previstos e fixar limiar 0,85. Imagens cortadas ou abaixo desse valor vão à revisão humana. Não treinar modelo nem alterar pré-processador.

## 3. Protocolo e critérios

Trinta imagens sintéticas: 20 legíveis, cinco com corte e cinco com sombra forte. Extrair campos das 20 legíveis e enviar as dez restantes à fila.

## 4. Parâmetros, versões e execução registrada

- limiar: 0.85

Versões localizadas: ocr-conf85-v1. Configuração estruturada: `configuracao.json`. Datas e estados: `cronologia.csv`.

## 5. Leitura e reconstrução dos resultados

`medicoes.csv` é a fonte dos contadores por cenário e das medições numéricas entregues. `resultados.csv` é calculado a partir dela, não é uma segunda confirmação independente. Para contadores, somar numeradores e denominadores apenas dentro de um ensaio. Ensaios diferentes podem compartilhar a população. Em resultados.csv, base_de_calculo preserva o total de referência e descricao_base explica o que ele representa. Para média, mediana e diferença entre maior e menor valor, usar a operação indicada. Para percentil_95 de histograma, ordenar valores e localizar o posto teto(0,95 × soma dos pesos). valor_observado reproduz uma medição única. indicador_precalculado transcreve um indicador já calculado: conferir essa transcrição não reproduz seu cálculo original. O LEIA_ME contém o dicionário completo.

Os arquivos não contêm transações bancárias nem uma implementação completa do sistema descrito. São registros primários fictícios do exercício. `entradas.csv` e `observacoes.csv` contêm recortes explicitamente identificados; não pretendem conter todas as entradas da população de um contador. A semente, quando informada, identifica o desenho sintético do cenário, não um executável ausente.

## 6. Limite da conclusão

As verificações são de aceite do produto e de sua fila de exceções. Não demonstram desenvolvimento de outro método de leitura.

## 7. Continuidade e detalhamento técnico

Executar a inclusão de imagens com novos padrões de legibilidade ao aceite do leitor e conferir o encaminhamento à fila de exceções.

As especificações descrevem o recorte sintético e não equivalem a um programa executável de produção.
