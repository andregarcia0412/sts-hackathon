# PRJ10 — Método e referência

Documento sintético. Data de corte: 2025-08-11.

## 1. Referência anterior

O fluxo de consentimento prevê iniciar no aplicativo e cancelar no portal. Existe diagrama com autorização, revogação e expiração, mas nenhuma tabela de precedência de eventos concorrentes aprovada.

Os catálogos/manuais citados neste documento são extratos fictícios definidos acima; não são documentos internos de instituição real. O trecho fornecido descreve as funções relevantes à comparação.

## 2. Mecanismo e hipótese

Minuta da máquina de estados lista iniciar→pendente→autorizado e revogar→revogado. Não define empate entre confirmação e revogação, relógio de referência ou política de idempotência.

## 3. Protocolo e critérios

Foram entregues oito eventos sintéticos de navegação e o diagrama. Quatro eventos têm um identificador de sessão e quatro não; nenhum contém a decisão de estado retornada pelo serviço. O memorando afirma redução de divergências sem preservar o antes/depois.

## 4. Parâmetros, versões e execução registrada

- versao_executada: null
- precedencia_empate: null

Versões localizadas: eventos-v1. Configuração estruturada: `configuracao.json`. Datas e estados: `cronologia.csv`.

## 5. Leitura e reconstrução dos resultados

`medicoes.csv` é a fonte dos contadores por cenário e das medições numéricas entregues. `resultados.csv` é calculado a partir dela, não é uma segunda confirmação independente. Para contadores, somar numeradores e denominadores apenas dentro de um ensaio. Ensaios diferentes podem compartilhar a população. Em resultados.csv, base_de_calculo preserva o total de referência e descricao_base explica o que ele representa. Para média, mediana e diferença entre maior e menor valor, usar a operação indicada. Para percentil_95 de histograma, ordenar valores e localizar o posto teto(0,95 × soma dos pesos). valor_observado reproduz uma medição única. indicador_precalculado transcreve um indicador já calculado: conferir essa transcrição não reproduz seu cálculo original. O LEIA_ME contém o dicionário completo.

Os arquivos não contêm transações bancárias nem uma implementação completa do sistema descrito. São registros primários fictícios do exercício. `entradas.csv` e `observacoes.csv` contêm recortes explicitamente identificados; não pretendem conter todas as entradas da população de um contador. A semente, quando informada, identifica o desenho sintético do cenário, não um executável ausente.

## 6. Limite da conclusão

Faltam versão executada, ordem causal confiável e saídas de estado. O diagrama por si só não prova execução do mecanismo proposto.

## 7. Continuidade e detalhamento técnico

Executar a vinculação de eventos de consentimento à sessão, à ordem causal e ao estado produzido pela máquina utilizada.

As especificações descrevem o recorte sintético e não equivalem a um programa executável de produção.
