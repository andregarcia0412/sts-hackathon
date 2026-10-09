# PRJ06 — Método e referência

Documento sintético. Data de corte: 2025-03-24.

## 1. Referência anterior

Última gravação vence ignora intenção; mesclagem de três vias preserva campos independentes, mas não a relação entre valor e anexo quando edições offline mudam ambos. Esses dois comparadores estão especificados e medidos.

Os catálogos/manuais citados neste documento são extratos fictícios definidos acima; não são documentos internos de instituição real. O trecho fornecido descreve as funções relevantes à comparação.

## 2. Mecanismo e hipótese

Representar edição como (campo, versão-base, intenção, dependência). Mesclar operações de campos independentes; para valor e anexo, aceitar automaticamente somente se a versão-base do documento confirma o mesmo valor. Em conflito dependente, produzir duas alternativas preservadas para escolha humana. A incerteza era obter automação sem apagar a dependência semântica.

## 3. Protocolo e critérios

90 conflitos: 30 campos simples, 30 anexos e 30 listas. Mesmas versões iniciais e edições em todas as estratégias. O conjunto contém 16 conflitos dependentes que exigem decisão humana. Última gravação perde conteúdo em 11; mesclagem proposta resolve 74 e encaminha 16 sem perda silenciosa.

## 4. Parâmetros, versões e execução registrada

- semente: 202506
- classes_conflito: ["campos", "anexos", "listas"]

Versões localizadas: ultima-v1, tresvias-v2, dependencia-v3. Configuração estruturada: `configuracao.json`. Datas e estados: `cronologia.csv`.

## 5. Leitura e reconstrução dos resultados

`medicoes.csv` é a fonte dos contadores por cenário e das medições numéricas entregues. `resultados.csv` é calculado a partir dela, não é uma segunda confirmação independente. Para contadores, somar numeradores e denominadores apenas dentro de um ensaio. Ensaios diferentes podem compartilhar a população. Em resultados.csv, base_de_calculo preserva o total de referência e descricao_base explica o que ele representa. Para média, mediana e diferença entre maior e menor valor, usar a operação indicada. Para percentil_95 de histograma, ordenar valores e localizar o posto teto(0,95 × soma dos pesos). valor_observado reproduz uma medição única. indicador_precalculado transcreve um indicador já calculado: conferir essa transcrição não reproduz seu cálculo original. O LEIA_ME contém o dicionário completo.

Os arquivos não contêm transações bancárias nem uma implementação completa do sistema descrito. São registros primários fictícios do exercício. `entradas.csv` e `observacoes.csv` contêm recortes explicitamente identificados; não pretendem conter todas as entradas da população de um contador. A semente, quando informada, identifica o desenho sintético do cenário, não um executável ausente.

## 6. Limite da conclusão

As listas ensaiadas contêm inserção e edição, mas não exclusão concorrente de item já referenciado por anexo. A hipótese de preservação dessa dependência permanece em aberto e integra a pretensão original.

## 7. Continuidade e detalhamento técnico

Executar a introdução de exclusão concorrente de item referenciado por anexo e observar a preservação da dependência na reconexão.

As especificações descrevem o recorte sintético e não equivalem a um programa executável de produção.
