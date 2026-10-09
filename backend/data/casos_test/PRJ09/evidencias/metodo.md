# PRJ09 — Método e referência

Documento sintético. Data de corte: 2025-07-07.

## 1. Referência anterior

O manual fictício GATE-4 define roteamento por cabeçalho api_version, transformação de campos e validação por contratos. A receita de coexistência é anterior à equipe.

Os catálogos/manuais citados neste documento são extratos fictícios definidos acima; não são documentos internos de instituição real. O trecho fornecido descreve as funções relevantes à comparação.

## 2. Mecanismo e hipótese

Cadastrar rotas v1/v2 e mapear campo total_centavos para total_decimal dividindo por 100; preservar campos obrigatórios. Ajustar escopo de permissão do conector, sem modificar motor de roteamento.

## 3. Protocolo e critérios

Vinte contratos por versão, 40 ao todo. Uma permissão incorreta na primeira rodada bloqueou dois contratos; todos passaram após correção.

## 4. Parâmetros, versões e execução registrada



Versões localizadas: rotas-v1, rotas-v2. Configuração estruturada: `configuracao.json`. Datas e estados: `cronologia.csv`.

## 5. Leitura e reconstrução dos resultados

`medicoes.csv` é a fonte dos contadores por cenário e das medições numéricas entregues. `resultados.csv` é calculado a partir dela, não é uma segunda confirmação independente. Para contadores, somar numeradores e denominadores apenas dentro de um ensaio. Ensaios diferentes podem compartilhar a população. Em resultados.csv, base_de_calculo preserva o total de referência e descricao_base explica o que ele representa. Para média, mediana e diferença entre maior e menor valor, usar a operação indicada. Para percentil_95 de histograma, ordenar valores e localizar o posto teto(0,95 × soma dos pesos). valor_observado reproduz uma medição única. indicador_precalculado transcreve um indicador já calculado: conferir essa transcrição não reproduz seu cálculo original. O LEIA_ME contém o dicionário completo.

Os arquivos não contêm transações bancárias nem uma implementação completa do sistema descrito. São registros primários fictícios do exercício. `entradas.csv` e `observacoes.csv` contêm recortes explicitamente identificados; não pretendem conter todas as entradas da população de um contador. A semente, quando informada, identifica o desenho sintético do cenário, não um executável ausente.

## 6. Limite da conclusão

O termo adaptativo no título comercial se refere à escolha de rota por versão. Não há inferência ou técnica nova de adaptação.

## 7. Continuidade e detalhamento técnico

Executar a inclusão de uma versão de contrato de API à tabela de rotas e conferir a resposta dos clientes dessa versão.

As especificações descrevem o recorte sintético e não equivalem a um programa executável de produção.
