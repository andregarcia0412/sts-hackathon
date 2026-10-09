# PRJ01 — Método e referência

Documento sintético. Data de corte: 2025-04-07.

## 1. Referência anterior

O manual fictício BARR-2, seção 4, anterior à configuração, fornece chave composta por operação e versão, retenção de duplicatas e distinção entre reenvio e nova operação.

Os catálogos/manuais citados neste documento são extratos fictícios definidos acima; não são documentos internos de instituição real. O trecho fornecido descreve as funções relevantes à comparação.

## 2. Mecanismo e hipótese

Configurar deduplicação por (operação, versão). Uma retransmissão mantém a chave; uma operação legítima nova recebe outra. Alterar retenção de 30 para 120 segundos, conforme faixa de 10–300 segundos já admitida pelo produto. Nenhum algoritmo do barramento foi modificado.

## 3. Protocolo e critérios

Sessenta roteiros: 40 envios únicos, 12 retransmissões da mesma chave e oito operações novas após interrupção. A rodada deduplicacao-v1 reteve oito duplicatas; deduplicacao-v2 reteve as 12. As oito operações novas foram liberadas em ambas.

## 4. Parâmetros, versões e execução registrada

- retencao_inicial_s: 30
- retencao_final_s: 120

Versões localizadas: deduplicacao-v1, deduplicacao-v2. Configuração estruturada: `configuracao.json`. Datas e estados: `cronologia.csv`.

## 5. Leitura e reconstrução dos resultados

`medicoes.csv` é a fonte dos contadores por cenário e das medições numéricas entregues. `resultados.csv` é calculado a partir dela, não é uma segunda confirmação independente. Para contadores, somar numeradores e denominadores apenas dentro de um ensaio. Ensaios diferentes podem compartilhar a população. Em resultados.csv, base_de_calculo preserva o total de referência e descricao_base explica o que ele representa. Para média, mediana e diferença entre maior e menor valor, usar a operação indicada. Para percentil_95 de histograma, ordenar valores e localizar o posto teto(0,95 × soma dos pesos). valor_observado reproduz uma medição única. indicador_precalculado transcreve um indicador já calculado: conferir essa transcrição não reproduz seu cálculo original. O LEIA_ME contém o dicionário completo.

Os arquivos não contêm transações bancárias nem uma implementação completa do sistema descrito. São registros primários fictícios do exercício. `entradas.csv` e `observacoes.csv` contêm recortes explicitamente identificados; não pretendem conter todas as entradas da população de um contador. A semente, quando informada, identifica o desenho sintético do cenário, não um executável ausente.

## 6. Limite da conclusão

Aceite limitado aos conectores e à janela configurada. Não há hipótese de mecanismo novo, apenas adequação da configuração ao contrato.

## 7. Continuidade e detalhamento técnico

Executar a conferência da janela de retenção de duplicatas quando um novo conector entrar no contrato de mensagens.

As especificações descrevem o recorte sintético e não equivalem a um programa executável de produção.
