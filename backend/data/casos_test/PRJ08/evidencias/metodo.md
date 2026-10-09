# PRJ08 — Método e referência

Documento sintético. Data de corte: 2025-06-02.

## 1. Referência anterior

Há um extrato de catálogo de sondas TCP/HTTP e uma topologia de três pontos. A equipe propôs distinguir enlace, aplicação e equipamento, mas não preservou uma regra de decisão executada.

Os catálogos/manuais citados neste documento são extratos fictícios definidos acima; não são documentos internos de instituição real. O trecho fornecido descreve as funções relevantes à comparação.

## 2. Mecanismo e hipótese

Plano propõe comparar latência local, disponibilidade do endpoint e heartbeat. Documento de desenho contém tabela de combinações possíveis, sem limiares aprovados nem associação das medições a causas injetadas.

## 3. Protocolo e critérios

Seis medições de disponibilidade foram recuperadas com timestamps e origem. Nenhuma tem causa controlada ou saída do classificador. Um memorando de demonstração afirma três causas separadas, sem vincular o número a esses seis registros.

## 4. Parâmetros, versões e execução registrada

- protocolo: "protocolo-documental"
- limiares: null
- versao_classificador: null

Versões localizadas: sonda-v1. Configuração estruturada: `configuracao.json`. Datas e estados: `cronologia.csv`.

## 5. Leitura e reconstrução dos resultados

`medicoes.csv` é a fonte dos contadores por cenário e das medições numéricas entregues. `resultados.csv` é calculado a partir dela, não é uma segunda confirmação independente. Para contadores, somar numeradores e denominadores apenas dentro de um ensaio. Ensaios diferentes podem compartilhar a população. Em resultados.csv, base_de_calculo preserva o total de referência e descricao_base explica o que ele representa. Para média, mediana e diferença entre maior e menor valor, usar a operação indicada. Para percentil_95 de histograma, ordenar valores e localizar o posto teto(0,95 × soma dos pesos). valor_observado reproduz uma medição única. indicador_precalculado transcreve um indicador já calculado: conferir essa transcrição não reproduz seu cálculo original. O LEIA_ME contém o dicionário completo.

Os arquivos não contêm transações bancárias nem uma implementação completa do sistema descrito. São registros primários fictícios do exercício. `entradas.csv` e `observacoes.csv` contêm recortes explicitamente identificados; não pretendem conter todas as entradas da população de um contador. A semente, quando informada, identifica o desenho sintético do cenário, não um executável ausente.

## 6. Limite da conclusão

Faltam versão do classificador, causas de referência e decisões por evento. Os registros sintéticos documentam a coleta, mas não o resultado alegado de classificação.

## 7. Continuidade e detalhamento técnico

Executar a associação das sondas TCP/HTTP a causas injetadas e registrar a decisão do classificador junto de cada timestamp.

As especificações descrevem o recorte sintético e não equivalem a um programa executável de produção.
