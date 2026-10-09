# PRJ13 — Método e referência

Documento sintético. Data de corte: 2025-05-19.

## 1. Referência anterior

Limite fixo, perfil mensal e atualização exponencial contínua são conhecidos. Na sequência estudada, a atualização contínua incorpora eventos ainda não revisados e desloca o perfil em direção a ataques persistentes.

Os catálogos/manuais citados neste documento são extratos fictícios definidos acima; não são documentos internos de instituição real. O trecho fornecido descreve as funções relevantes à comparação.

## 2. Mecanismo e hipótese

Manter centro e dispersão robustos por segmento. Eventos alertados entram em quarentena; só atualizar o perfil após confirmação de legitimidade. Abrir nova faixa sazonal quando a mudança persiste por três janelas sem aumento de rótulos fraudulentos. Usar faixa de confiança de 2,5 desvios nos segmentos frequentes e 3,0 nos dois segmentos escassos, definidos na preparação. A hipótese é distinguir mudança legítima e contaminação sem perder sensibilidade.

## 3. Protocolo e critérios

40 mil transações: 36 mil legítimas e quatro mil fraudes, distribuídas igualmente em quatro deslocamentos sazonais. Comparar limite fixo, perfil mensal, atualização contínua e atualização condicionada. Todos usam mesma ordem, rótulos e corte temporal; rótulo só é disponibilizado ao atualizador após atraso de 20 eventos. Critérios prévios: falso alerta ≤ 4% nas legítimas e sensibilidade>90% em cada deslocamento.

## 4. Parâmetros, versões e execução registrada

- semente: 202513
- janela_eventos: 250
- atraso_rotulo_eventos: 20
- deslocamentos: 4
- segmentos_escassos: ["S5", "S6"]

Versões localizadas: fixo-v1, mensal-v2, continuo-v3, condicionado-v4. Configuração estruturada: `configuracao.json`. Datas e estados: `cronologia.csv`.

## 5. Leitura e reconstrução dos resultados

`medicoes.csv` é a fonte dos contadores por cenário e das medições numéricas entregues. `resultados.csv` é calculado a partir dela, não é uma segunda confirmação independente. Para contadores, somar numeradores e denominadores apenas dentro de um ensaio. Ensaios diferentes podem compartilhar a população. Em resultados.csv, base_de_calculo preserva o total de referência e descricao_base explica o que ele representa. Para média, mediana e diferença entre maior e menor valor, usar a operação indicada. Para percentil_95 de histograma, ordenar valores e localizar o posto teto(0,95 × soma dos pesos). valor_observado reproduz uma medição única. indicador_precalculado transcreve um indicador já calculado: conferir essa transcrição não reproduz seu cálculo original. O LEIA_ME contém o dicionário completo.

Os arquivos não contêm transações bancárias nem uma implementação completa do sistema descrito. São registros primários fictícios do exercício. `entradas.csv` e `observacoes.csv` contêm recortes explicitamente identificados; não pretendem conter todas as entradas da população de um contador. A semente, quando informada, identifica o desenho sintético do cenário, não um executável ausente.

## 6. Limite da conclusão

A documentação permite reconstruir as contagens nos quatro deslocamentos sintéticos. Não se reivindica validade para distribuições externas.

## 7. Continuidade e detalhamento técnico

Executar a variação do atraso de disponibilização dos rótulos e observar a contaminação do perfil e os falsos alertas por deslocamento sazonal.

As especificações descrevem o recorte sintético e não equivalem a um programa executável de produção.

```text
para evento em ordem temporal:
  estimar_faixa(segmento, centro_robusto, dispersao)
  se fora_da_faixa: quarentena.adicionar(evento)
  quando rotulo chega apos 20 eventos:
    se legitimo: atualizar_perfil_sem_usar_eventos_pendentes()
  se mudanca_persiste_3_janelas e fraude_nao_aumentou:
    abrir_faixa_sazonal_preservando_perfil_anterior()
```


