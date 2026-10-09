# PRJ11 — Método e referência

Documento sintético. Data de corte: 2025-03-10.

## 1. Referência anterior

O dicionário fictício DIC-11/v3 antecede o projeto: tipo CC→corrente, PP→poupança; data ISO; valor ausente permanece nulo; origem desconhecida é rejeitada.

Os catálogos/manuais citados neste documento são extratos fictícios definidos acima; não são documentos internos de instituição real. O trecho fornecido descreve as funções relevantes à comparação.

## 2. Mecanismo e hipótese

Aplicar mapeamento por origem e validar tipo, domínio e ausência. Não inferir categorias nem estimar valores. Corrigir três cadastros de origem e repetir a mesma carga.

## 3. Protocolo e critérios

Cem registros sintéticos de duas origens; três rejeições por código fora do dicionário na primeira passagem. Após correção cadastral, 100 conformes.

## 4. Parâmetros, versões e execução registrada



Versões localizadas: carga-v1, carga-v2. Configuração estruturada: `configuracao.json`. Datas e estados: `cronologia.csv`.

## 5. Leitura e reconstrução dos resultados

`medicoes.csv` é a fonte dos contadores por cenário e das medições numéricas entregues. `resultados.csv` é calculado a partir dela, não é uma segunda confirmação independente. Para contadores, somar numeradores e denominadores apenas dentro de um ensaio. Ensaios diferentes podem compartilhar a população. Em resultados.csv, base_de_calculo preserva o total de referência e descricao_base explica o que ele representa. Para média, mediana e diferença entre maior e menor valor, usar a operação indicada. Para percentil_95 de histograma, ordenar valores e localizar o posto teto(0,95 × soma dos pesos). valor_observado reproduz uma medição única. indicador_precalculado transcreve um indicador já calculado: conferir essa transcrição não reproduz seu cálculo original. O LEIA_ME contém o dicionário completo.

Os arquivos não contêm transações bancárias nem uma implementação completa do sistema descrito. São registros primários fictícios do exercício. `entradas.csv` e `observacoes.csv` contêm recortes explicitamente identificados; não pretendem conter todas as entradas da população de um contador. A semente, quando informada, identifica o desenho sintético do cenário, não um executável ausente.

## 6. Limite da conclusão

O escopo é conformidade com dicionário aprovado. Nenhum novo método de normalização foi proposto ou testado.

## 7. Continuidade e detalhamento técnico

Executar a inclusão de novos exemplos de valores nulos e conferir a normalização contra o dicionário de contas aprovado.

As especificações descrevem o recorte sintético e não equivalem a um programa executável de produção.
