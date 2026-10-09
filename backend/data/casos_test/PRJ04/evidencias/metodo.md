# PRJ04 — Método e referência

Documento sintético. Data de corte: 2025-07-21.

## 1. Referência anterior

O catálogo fictício VIS-3 já fornece junção por correlation_id, mascaramento por perfil e filtros. Os três sistemas de origem emitem esse identificador.

Os catálogos/manuais citados neste documento são extratos fictícios definidos acima; não são documentos internos de instituição real. O trecho fornecido descreve as funções relevantes à comparação.

## 2. Mecanismo e hipótese

Configurar consulta por correlation_id e máscara de campos conforme matriz de acesso. O perfil consulta recebe somente valor mascarado; o perfil conciliação recebe detalhe. Corrigir uma permissão excessiva no mapeamento do perfil.

## 3. Protocolo e critérios

Doze roteiros sobre três sistemas e dois perfis. A primeira matriz permitiu detalhe em um roteiro indevido; a segunda cumpriu os 12 resultados esperados.

## 4. Parâmetros, versões e execução registrada



Versões localizadas: matriz-v1, matriz-v2. Configuração estruturada: `configuracao.json`. Datas e estados: `cronologia.csv`.

## 5. Leitura e reconstrução dos resultados

`medicoes.csv` é a fonte dos contadores por cenário e das medições numéricas entregues. `resultados.csv` é calculado a partir dela, não é uma segunda confirmação independente. Para contadores, somar numeradores e denominadores apenas dentro de um ensaio. Ensaios diferentes podem compartilhar a população. Em resultados.csv, base_de_calculo preserva o total de referência e descricao_base explica o que ele representa. Para média, mediana e diferença entre maior e menor valor, usar a operação indicada. Para percentil_95 de histograma, ordenar valores e localizar o posto teto(0,95 × soma dos pesos). valor_observado reproduz uma medição única. indicador_precalculado transcreve um indicador já calculado: conferir essa transcrição não reproduz seu cálculo original. O LEIA_ME contém o dicionário completo.

Os arquivos não contêm transações bancárias nem uma implementação completa do sistema descrito. São registros primários fictícios do exercício. `entradas.csv` e `observacoes.csv` contêm recortes explicitamente identificados; não pretendem conter todas as entradas da população de um contador. A semente, quando informada, identifica o desenho sintético do cenário, não um executável ausente.

## 6. Limite da conclusão

Verificação funcional de acesso e visualização. Não se investigou técnica nova de inferência ou reconstrução de trilha.

## 7. Continuidade e detalhamento técnico

Executar a inclusão, no roteiro do painel, das combinações de perfil de acesso solicitadas pela conciliação.

As especificações descrevem o recorte sintético e não equivalem a um programa executável de produção.
