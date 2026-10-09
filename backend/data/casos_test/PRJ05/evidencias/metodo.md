# PRJ05 — Método e referência

Documento sintético. Data de corte: 2025-08-25.

## 1. Referência anterior

Banco local cifrado e chave por sessão eram conhecidos. O comparador BASE-OFF-1 usa uma chave persistente por perfil; a alternativa chave efêmera por formulário já conhecida perde recuperação após suspensão. O problema investigado é recuperar blocos após queda de rede e suspender acesso após troca de usuário, com transições concorrentes do processo.

Os catálogos/manuais citados neste documento são extratos fictícios definidos acima; não são documentos internos de instituição real. O trecho fornecido descreve as funções relevantes à comparação.

## 2. Mecanismo e hipótese

Protótipo mantém blocos cifrados associados a época de sessão. Antes de trocar usuário, grava marcador de revogação e incrementa época; na retomada, aceita bloco apenas se época do cabeçalho coincide com a sessão e o marcador não o revoga. A hipótese combina recuperação de gravação parcial e invalidação lógica antes da remoção física da chave. Não envolve inventar cifra ou apresentar dados reais.

## 3. Protocolo e critérios

24 roteiros em três pontos de queda de rede e duas trocas de sessão. Banco local recuperou 24, mas deixou dois roteiros de troca acessíveis ao usuário seguinte. Blocos por época recuperaram 24 e bloquearam leitura indevida nas oito trocas. Há oito testes de retomada por alternativa efêmera, dos quais seis perderam o formulário.

## 4. Parâmetros, versões e execução registrada

- semente: 202505
- epocas: [7, 8]
- janelas_queda: ["antes", "durante", "depois"]
- corte_energia_executado: false

Versões localizadas: banco-v1, epoca-v2, efemera-v3. Configuração estruturada: `configuracao.json`. Datas e estados: `cronologia.csv`.

## 5. Leitura e reconstrução dos resultados

`medicoes.csv` é a fonte dos contadores por cenário e das medições numéricas entregues. `resultados.csv` é calculado a partir dela, não é uma segunda confirmação independente. Para contadores, somar numeradores e denominadores apenas dentro de um ensaio. Ensaios diferentes podem compartilhar a população. Em resultados.csv, base_de_calculo preserva o total de referência e descricao_base explica o que ele representa. Para média, mediana e diferença entre maior e menor valor, usar a operação indicada. Para percentil_95 de histograma, ordenar valores e localizar o posto teto(0,95 × soma dos pesos). valor_observado reproduz uma medição única. indicador_precalculado transcreve um indicador já calculado: conferir essa transcrição não reproduz seu cálculo original. O LEIA_ME contém o dicionário completo.

Os arquivos não contêm transações bancárias nem uma implementação completa do sistema descrito. São registros primários fictícios do exercício. `entradas.csv` e `observacoes.csv` contêm recortes explicitamente identificados; não pretendem conter todas as entradas da população de um contador. A semente, quando informada, identifica o desenho sintético do cenário, não um executável ausente.

## 6. Limite da conclusão

O protocolo inclui uma hipótese sobre interrupção abrupta entre gravação do marcador e eliminação da chave. Corte de energia nessa janela não foi ensaiado. A evidência sustenta a investigação e a solução para quedas de rede, mas não a alegação de revogação em qualquer encerramento.

## 7. Continuidade e detalhamento técnico

Executar a interrupção da alimentação entre o marcador de revogação e a remoção da chave; inspecionar o acesso aos blocos após reinício.

As especificações descrevem o recorte sintético e não equivalem a um programa executável de produção.
