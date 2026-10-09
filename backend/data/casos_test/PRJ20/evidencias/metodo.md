# PRJ20 — Método e referência

Documento sintético. Data de corte: 2025-07-14.

## 1. Referência anterior

A plataforma fictícia SIM-4 oferece modo sombra, duplicação da solicitação, supressão de efeitos e comparação de saídas. O manual anterior prevê especificamente que apenas o motor principal emita contratos.

Os catálogos/manuais citados neste documento são extratos fictícios definidos acima; não são documentos internos de instituição real. O trecho fornecido descreve as funções relevantes à comparação.

## 2. Mecanismo e hipótese

Ativar shadow=true, write_side_effects=false e comparar campos decisao e motivo. Selecionar divergências para revisão de negócio. As regras e o mecanismo de isolamento foram fornecidos pela plataforma; não houve alteração do comparador ou hipótese sobre mecanismo novo.

## 3. Protocolo e critérios

18 mil propostas idênticas enviadas aos dois motores. 430 divergências correspondem às diferenças de política cadastradas; zero contratos emitidos pelo motor sombra. O roteiro verifica configuração e equivalência de entradas.

## 4. Parâmetros, versões e execução registrada

- shadow: true
- write_side_effects: false
- campos_comparados: ["decisao", "motivo"]

Versões localizadas: sombra-v1. Configuração estruturada: `configuracao.json`. Datas e estados: `cronologia.csv`.

## 5. Leitura e reconstrução dos resultados

`medicoes.csv` é a fonte dos contadores por cenário e das medições numéricas entregues. `resultados.csv` é calculado a partir dela, não é uma segunda confirmação independente. Para contadores, somar numeradores e denominadores apenas dentro de um ensaio. Ensaios diferentes podem compartilhar a população. Em resultados.csv, base_de_calculo preserva o total de referência e descricao_base explica o que ele representa. Para média, mediana e diferença entre maior e menor valor, usar a operação indicada. Para percentil_95 de histograma, ordenar valores e localizar o posto teto(0,95 × soma dos pesos). valor_observado reproduz uma medição única. indicador_precalculado transcreve um indicador já calculado: conferir essa transcrição não reproduz seu cálculo original. O LEIA_ME contém o dicionário completo.

Os arquivos não contêm transações bancárias nem uma implementação completa do sistema descrito. São registros primários fictícios do exercício. `entradas.csv` e `observacoes.csv` contêm recortes explicitamente identificados; não pretendem conter todas as entradas da população de um contador. A semente, quando informada, identifica o desenho sintético do cenário, não um executável ausente.

## 6. Limite da conclusão

Resultados não demonstram avanço tecnológico. Executar novamente pode ampliar confiança operacional, mas não transforma a configuração documentada em pesquisa.

## 7. Continuidade e detalhamento técnico

Executar a conferência da supressão de emissão no motor sombra após a próxima atualização das políticas de decisão.

As especificações descrevem o recorte sintético e não equivalem a um programa executável de produção.
