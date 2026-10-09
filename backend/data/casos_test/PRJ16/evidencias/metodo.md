# PRJ16 — Método e referência

Documento sintético. Data de corte: 2025-09-01.

## 1. Referência anterior

Roteiro manual e replay por tempo de captura reproduzem requisições, mas podem inverter precedência quando a troca de dispositivo altera o atraso de processamento.

Os catálogos/manuais citados neste documento são extratos fictícios definidos acima; não são documentos internos de instituição real. O trecho fornecido descreve as funções relevantes à comparação.

## 2. Mecanismo e hipótese

Grafo acíclico com eventos e dependências; fila de prontos ordenada por (tempo lógico, sequência da origem, ID do evento). Um relógio virtual de injeção controla atrasos, sem substituir o relógio interno do serviço. Só liberar evento depois dos predecessores confirmados. Empates são resolvidos por sequência/ID, correção documentada em causal-v3.

## 3. Protocolo e critérios

32 ataques com cinco repetições cada, total 160. Manual, replay e gerador causal com mesma matriz de entrada. Critério: ordem parcial válida e estado terminal equivalente. Duas falhas intermitentes são identificadas por cenário e reproduzidas nas cinco repetições; não significam duas falhas em cada execução.

## 4. Parâmetros, versões e execução registrada

- semente: 202516
- ataques: 32
- repeticoes: 5
- desempate: ["tempo_logico", "sequencia_origem", "id_evento"]

Versões localizadas: manual-v1, replay-v2, causal-v3. Configuração estruturada: `configuracao.json`. Datas e estados: `cronologia.csv`.

## 5. Leitura e reconstrução dos resultados

`medicoes.csv` é a fonte dos contadores por cenário e das medições numéricas entregues. `resultados.csv` é calculado a partir dela, não é uma segunda confirmação independente. Para contadores, somar numeradores e denominadores apenas dentro de um ensaio. Ensaios diferentes podem compartilhar a população. Em resultados.csv, base_de_calculo preserva o total de referência e descricao_base explica o que ele representa. Para média, mediana e diferença entre maior e menor valor, usar a operação indicada. Para percentil_95 de histograma, ordenar valores e localizar o posto teto(0,95 × soma dos pesos). valor_observado reproduz uma medição única. indicador_precalculado transcreve um indicador já calculado: conferir essa transcrição não reproduz seu cálculo original. O LEIA_ME contém o dicionário completo.

Os arquivos não contêm transações bancárias nem uma implementação completa do sistema descrito. São registros primários fictícios do exercício. `entradas.csv` e `observacoes.csv` contêm recortes explicitamente identificados; não pretendem conter todas as entradas da população de um contador. A semente, quando informada, identifica o desenho sintético do cenário, não um executável ausente.

Estado terminal equivalente significa equivalência à referência da especificação de cada cenário, incluindo o comportamento observado do sistema avaliado. As duas falhas de bloqueio do ensaio PRJ16-S04, nos cenários S07 e S19, são resultados reproduzidos do sistema sob teste; não são divergências de reprodução da ordem ou do estado de referência pelo simulador.

## 6. Limite da conclusão

O pacote contém grafo de exemplo, regra de ordenação, configuração e registros por cenário. Não inclui ambiente de integração; a transferência é da especificação e dos resultados sintéticos.

## 7. Continuidade e detalhamento técnico

Executar a ampliação do catálogo de sequências de ataque e registrar separadamente a reprodução da ordem e o bloqueio pelo sistema avaliado.

As especificações descrevem o recorte sintético e não equivalem a um programa executável de produção.

```text
prontos = eventos_sem_predecessor
enquanto houver evento:
  escolher(prontos, chave=(tempo_logico, sequencia_origem, id))
  aguardar_atraso_virtual_de_injecao(); injetar_sem_trocar_relogio_do_servico()
  registrar_confirmacao_origem_sequencia_estado()
  liberar_sucessores_com_todos_predecessores_confirmados()
```



`configuracao.json` entrega os 32 grafos com eventos, predecessores, atrasos e sementes. A ordem parcial é dada pelas arestas; eventos sem caminho causal entre si podem ocorrer em qualquer ordem sem constituir divergência.
