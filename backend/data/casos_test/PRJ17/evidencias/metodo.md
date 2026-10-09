# PRJ17 — Método e referência

Documento sintético. Data de corte: 2025-03-31.

## 1. Referência anterior

O plano contrapõe política vigente e política candidata, mas as regras são identificadas apenas como antiga/nova. Não há tabelas de limiares nem versão assinada para nenhuma.

Os catálogos/manuais citados neste documento são extratos fictícios definidos acima; não são documentos internos de instituição real. O trecho fornecido descreve as funções relevantes à comparação.

## 2. Mecanismo e hipótese

Diagrama propõe duplicar uma proposta, executar duas políticas sem emitir contrato e comparar aprovação. Não define se o motor foi alterado ou se eram parâmetros do simulador comercial.

## 3. Protocolo e critérios

Há seis propostas sintéticas com renda e comprometimento e um memorando de demonstração que afirma impacto diferente. Não há decisões pareadas nem versão das políticas; as seis propostas não têm vínculo com a demonstração.

## 4. Parâmetros, versões e execução registrada

- versao_politica_antiga: null
- versao_politica_nova: null

Versões localizadas: entrada-v1. Configuração estruturada: `configuracao.json`. Datas e estados: `cronologia.csv`.

## 5. Leitura e reconstrução dos resultados

`medicoes.csv` é a fonte dos contadores por cenário e das medições numéricas entregues. `resultados.csv` é calculado a partir dela, não é uma segunda confirmação independente. Para contadores, somar numeradores e denominadores apenas dentro de um ensaio. Ensaios diferentes podem compartilhar a população. Em resultados.csv, base_de_calculo preserva o total de referência e descricao_base explica o que ele representa. Para média, mediana e diferença entre maior e menor valor, usar a operação indicada. Para percentil_95 de histograma, ordenar valores e localizar o posto teto(0,95 × soma dos pesos). valor_observado reproduz uma medição única. indicador_precalculado transcreve um indicador já calculado: conferir essa transcrição não reproduz seu cálculo original. O LEIA_ME contém o dicionário completo.

Os arquivos não contêm transações bancárias nem uma implementação completa do sistema descrito. São registros primários fictícios do exercício. `entradas.csv` e `observacoes.csv` contêm recortes explicitamente identificados; não pretendem conter todas as entradas da população de um contador. A semente, quando informada, identifica o desenho sintético do cenário, não um executável ausente.

## 6. Limite da conclusão

Sem regras e saídas não se avalia diferença técnica ou o número alegado. Os arquivos de entrada existentes não completam a cadeia.

## 7. Continuidade e detalhamento técnico

Executar a associação das propostas às políticas antiga e nova, incluindo as regras aplicadas e as decisões produzidas em cada simulação.

As especificações descrevem o recorte sintético e não equivalem a um programa executável de produção.
