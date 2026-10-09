# PRJ07 — Método e referência

Documento sintético. Data de corte: 2025-04-28.

## 1. Referência anterior

Biblioteca completa e versão leve de quadro único já estavam disponíveis. A completa usa 82 MB no pico; a leve cabe no limite de 32 MB, mas não vincula retomada ao desafio anterior quando a rede cai.

Os catálogos/manuais citados neste documento são extratos fictícios definidos acima; não são documentos internos de instituição real. O trecho fornecido descreve as funções relevantes à comparação.

## 2. Mecanismo e hipótese

Dividir captura, assinatura do transcript e envio. Cada etapa consome a anterior por nonce de uso único; assinatura cobre hash do transcript, época de sessão e contador da etapa. Retomar somente após confirmar consumo do último nonce; liberar buffers de imagem antes da assinatura. O problema era preservar vínculo entre etapas sob memória limitada e interrupção, não criar um algoritmo criptográfico.

## 3. Protocolo e critérios

300 sessões legítimas: três perfis de aparelho × quatro níveis de sinal × 25 sessões. Vinte replays em conjunto separado. Completa conclui 183/300, leve 255/300 e etapas 276/300; a leve aceita três replays e etapas nenhum dos 20.

## 4. Parâmetros, versões e execução registrada

- semente: 202507
- memoria_limite_mb: 32
- aparelhos: 3
- niveis_sinal: 4

Versões localizadas: completa-v1, leve-v2, etapas-v3. Configuração estruturada: `configuracao.json`. Datas e estados: `cronologia.csv`.

## 5. Leitura e reconstrução dos resultados

`medicoes.csv` é a fonte dos contadores por cenário e das medições numéricas entregues. `resultados.csv` é calculado a partir dela, não é uma segunda confirmação independente. Para contadores, somar numeradores e denominadores apenas dentro de um ensaio. Ensaios diferentes podem compartilhar a população. Em resultados.csv, base_de_calculo preserva o total de referência e descricao_base explica o que ele representa. Para média, mediana e diferença entre maior e menor valor, usar a operação indicada. Para percentil_95 de histograma, ordenar valores e localizar o posto teto(0,95 × soma dos pesos). valor_observado reproduz uma medição única. indicador_precalculado transcreve um indicador já calculado: conferir essa transcrição não reproduz seu cálculo original. O LEIA_ME contém o dicionário completo.

Os arquivos não contêm transações bancárias nem uma implementação completa do sistema descrito. São registros primários fictícios do exercício. `entradas.csv` e `observacoes.csv` contêm recortes explicitamente identificados; não pretendem conter todas as entradas da população de um contador. A semente, quando informada, identifica o desenho sintético do cenário, não um executável ausente.

## 6. Limite da conclusão

Não há teste de substituição do conteúdo entre captura e assinatura em processo comprometido. A conclusão anti-replay tem amostra delimitada; a pretensão de resistência a adulteração local ainda não foi validada.

## 7. Continuidade e detalhamento técnico

Executar a substituição do conteúdo entre captura e assinatura em processo comprometido, verificando o vínculo do transcript com o desafio.

As especificações descrevem o recorte sintético e não equivalem a um programa executável de produção.
