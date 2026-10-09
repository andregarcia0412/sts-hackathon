# PRJ03 — Método e referência

Documento sintético. Data de corte: 2025-06-16.

## 1. Referência anterior

Lote fixo e controle reativo pela latência eram conhecidos. Após duas falhas sucessivas, atraso da fila e latência do serviço davam sinais incompatíveis: o reativo acelerava ao ver fila envelhecida e recriava sobrecarga.

Os catálogos/manuais citados neste documento são extratos fictícios definidos acima; não são documentos internos de instituição real. O trecho fornecido descreve as funções relevantes à comparação.

## 2. Mecanismo e hipótese

A cada segundo medir p95 da latência em janela de 10 s e derivada do atraso da fila. Limitar lote a [50,1000]. Se p95>400 ms reduzir lote em 25%; se p95≤ 400 ms e atraso cresce, aumentar no máximo 5%; só voltar a acelerar após três janelas estáveis. O acoplamento com histerese, e não um novo nome para retry, foi confrontado com o controlador de latência isolado.

## 3. Protocolo e critérios

Seis cenários: filas de 5, 20 e 50 mil eventos × dois perfis de latência. Falhas nos instantes 30 s e 90 s, indisponibilidade de 10 s cada. Mesmas entradas e calendário nas três estratégias. A redução de 34% refere-se à fila de 50 mil no perfil L2: 1.000 s para 660 s.

## 4. Parâmetros, versões e execução registrada

- semente: 202503
- filas: [5000, 20000, 50000]
- perfis_ms: {"L1": [40, 200], "L2": [80, 600]}
- falhas_s: [30, 90]

Versões localizadas: fixo-v1, reativo-v2, duplo-v3. Configuração estruturada: `configuracao.json`. Datas e estados: `cronologia.csv`.

## 5. Leitura e reconstrução dos resultados

`medicoes.csv` é a fonte dos contadores por cenário e das medições numéricas entregues. `resultados.csv` é calculado a partir dela, não é uma segunda confirmação independente. Para contadores, somar numeradores e denominadores apenas dentro de um ensaio. Ensaios diferentes podem compartilhar a população. Em resultados.csv, base_de_calculo preserva o total de referência e descricao_base explica o que ele representa. Para média, mediana e diferença entre maior e menor valor, usar a operação indicada. Para percentil_95 de histograma, ordenar valores e localizar o posto teto(0,95 × soma dos pesos). valor_observado reproduz uma medição única. indicador_precalculado transcreve um indicador já calculado: conferir essa transcrição não reproduz seu cálculo original. O LEIA_ME contém o dicionário completo.

Os arquivos não contêm transações bancárias nem uma implementação completa do sistema descrito. São registros primários fictícios do exercício. `entradas.csv` e `observacoes.csv` contêm recortes explicitamente identificados; não pretendem conter todas as entradas da população de um contador. A semente, quando informada, identifica o desenho sintético do cenário, não um executável ausente.

O ganho de 34% compara uma única medição por estratégia na fila de 50 mil eventos, perfil L2: fixo-v1 = 1.000 s e duplo-v3 = 660 s (PRJ03-S04/S05). Não é uma média de ganhos nos seis cenários. O lote fixo também fecha 6/6 cenários sem terceira queda (PRJ03-S01); esse indicador de estabilidade, isoladamente, não demonstra superioridade do controle duplo.

## 6. Limite da conclusão

Duas falhas e latência nos perfis L1/L2 compõem o escopo de conclusão. Sequências mais longas não foram reivindicadas.

## 7. Continuidade e detalhamento técnico

Executar a medição do tempo de drenagem nas demais filas e perfis, mantendo o calendário das duas falhas e o comparador de lote fixo.

As especificações descrevem o recorte sintético e não equivalem a um programa executável de produção.

```text
lote = 200
a cada 1s:
  p95 = latencias_ultimos_10s.percentil(95)
  se p95 > 400ms: lote = max(50, lote*0.75); estaveis = 0
  senao: atualizar_janelas_estaveis()
  se estaveis >= 3 e derivada_atraso_fila > 0:
    lote = min(1000, lote*1.05)
  liberar_no_maximo(lote)
```



## 8. Leitura dos valores únicos

PRJ03-S04 e PRJ03-S05 contêm um tempo registrado por versão para a fila de 50 mil eventos no perfil L2. A operação valor_observado explicita essa medição única; não há média entre repetições nesses dois registros.
