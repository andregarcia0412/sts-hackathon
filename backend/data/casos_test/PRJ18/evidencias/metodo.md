# PRJ18 — Método e referência

Documento sintético. Data de corte: 2025-05-05.

## 1. Referência anterior

Log integral preserva fatos mas amplia latência; amostragem periódica perde mudanças de estado entre pontos. Ambos foram comparados na mesma carga, com o mesmo motor e regra de explicação.

Os catálogos/manuais citados neste documento são extratos fictícios definidos acima; não são documentos internos de instituição real. O trecho fornecido descreve as funções relevantes à comparação.

## 2. Mecanismo e hipótese

Emitir registro quando muda o estado lógico de regra, incluindo snapshot de fatos e ponteiro para predecessor; coalescer leituras sem mudança. A hipótese é conservar dependências decisórias com menos escrita. A versão seletiva ainda perde o predecessor quando um callback tardio chega após a coalescência.

## 3. Protocolo e critérios

50 mil decisões, quatro perfis. Log integral explica 100% com acréscimo de 24% na latência média; amostragem explica 82% com 3%; seletivo explica 96% com 7%. Critério prévio pretendia explicação de 100% e aumento de latência ≤ 10%. Os 2.000 casos sem trilha completa permanecem identificados por perfil.

## 4. Parâmetros, versões e execução registrada

- semente: 202518
- limite_acrescimo_latencia_pct: 10
- meta_explicacao_pct: 100

Versões localizadas: integral-v1, amostra-v2, seletivo-v3, semtrilha-v4. Configuração estruturada: `configuracao.json`. Datas e estados: `cronologia.csv`.

## 5. Leitura e reconstrução dos resultados

`medicoes.csv` é a fonte dos contadores por cenário e das medições numéricas entregues. `resultados.csv` é calculado a partir dela, não é uma segunda confirmação independente. Para contadores, somar numeradores e denominadores apenas dentro de um ensaio. Ensaios diferentes podem compartilhar a população. Em resultados.csv, base_de_calculo preserva o total de referência e descricao_base explica o que ele representa. Para média, mediana e diferença entre maior e menor valor, usar a operação indicada. Para percentil_95 de histograma, ordenar valores e localizar o posto teto(0,95 × soma dos pesos). valor_observado reproduz uma medição única. indicador_precalculado transcreve um indicador já calculado: conferir essa transcrição não reproduz seu cálculo original. O LEIA_ME contém o dicionário completo.

Os arquivos não contêm transações bancárias nem uma implementação completa do sistema descrito. São registros primários fictícios do exercício. `entradas.csv` e `observacoes.csv` contêm recortes explicitamente identificados; não pretendem conter todas as entradas da população de um contador. A semente, quando informada, identifica o desenho sintético do cenário, não um executável ausente.

## 6. Limite da conclusão

O tratamento de callback tardio segue aberto; o protótipo não satisfaz a exigência de explicação integral. A cronologia identifica as versões e o critério da rodada.

## 7. Continuidade e detalhamento técnico

Executar a instrumentação do callback tardio para verificar se a trilha seletiva conserva os fatos consumidos sem ultrapassar o limite de latência.

As especificações descrevem o recorte sintético e não equivalem a um programa executável de produção.
