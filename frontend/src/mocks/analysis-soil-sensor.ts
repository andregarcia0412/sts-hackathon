import type { Analysis, ProjectDocument } from "@/domain/types";
import {
  decreto5798,
  faqMcti,
  frascati,
  guiaMcti,
  inRfb1187,
  lei11196,
} from "@/mocks/references";

/*
 * EXEMPLO FICTÍCIO: análise completa (5 critérios) usada para desenvolver as
 * telas de análise e decisão. Empresa, documentos e trechos são inventados.
 */

export const soilSensorDocuments: ProjectDocument[] = [
  {
    id: "doc-1",
    fileName: "Plano_de_Projeto_EXEMPLO.pdf",
    mimeType: "application/pdf",
    sizeBytes: 1_842_311,
    uploadedAt: "2026-09-28T13:12:00.000Z",
  },
  {
    id: "doc-2",
    fileName: "Relatorio_Tecnico_2025_EXEMPLO.pdf",
    mimeType: "application/pdf",
    sizeBytes: 3_410_092,
    uploadedAt: "2026-09-28T13:12:00.000Z",
  },
  {
    id: "doc-3",
    fileName: "Cronograma_e_Orcamento_EXEMPLO.docx",
    mimeType:
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    sizeBytes: 228_740,
    uploadedAt: "2026-09-28T13:12:00.000Z",
  },
];

const plan = { documentId: "doc-1", fileName: "Plano_de_Projeto_EXEMPLO.pdf" };
const report = {
  documentId: "doc-2",
  fileName: "Relatorio_Tecnico_2025_EXEMPLO.pdf",
};
const schedule = {
  documentId: "doc-3",
  fileName: "Cronograma_e_Orcamento_EXEMPLO.docx",
};

export const soilSensorAnalysis: Analysis = {
  id: "an-soil-001",
  projectId: "p1",
  framework: "frascati",
  suggestedCategory: "DE",
  generatedAt: "2026-09-28T13:20:41.000Z",
  criteria: [
    {
      id: "crit-novelty",
      key: "novelty",
      name: "Novidade",
      score: 78,
      summary:
        "O projeto propõe um método de calibração do sensor que não aparece no estado da arte citado. Parte da solução, porém, usa componentes e protocolos de amplo domínio.",
      rules: [
        {
          id: "rule-proj-12",
          code: "PROJ-12",
          name: "Elemento tecnologicamente novo",
          score: 84,
          explanation:
            "O elemento novo está identificado (calibração por impedância com compensação de salinidade) e é comparado com soluções existentes no mercado e na literatura.",
          normativeSource: frascati("§§2.14–2.16"),
          evidences: [
            {
              id: "ev-1",
              title: "Comparação com o estado da arte",
              polarity: "positive",
              explanation:
                "O plano compara a proposta com três soluções comerciais e dois artigos, e aponta a lacuna técnica que nenhuma delas resolve.",
              projectExcerpt: {
                ...plan,
                page: 3,
                excerpt:
                  "Os sensores capacitivos disponíveis apresentam erro superior a 12% em solos com condutividade elétrica acima de 4 dS/m, condição comum no semiárido. Não foram encontradas soluções que compensem esse efeito em dispositivos de custo inferior a R$ 150.",
              },
              references: [frascati("§2.14"), guiaMcti("§6.1")],
            },
            {
              id: "ev-2",
              title: "Novidade em relação ao setor, não só à empresa",
              polarity: "positive",
              explanation:
                "O texto deixa claro que a novidade vale para o setor, o que é exigido pelo MCTI (não basta ser novo para a empresa).",
              projectExcerpt: {
                ...plan,
                page: 4,
                excerpt:
                  "A técnica de compensação proposta não foi identificada em produtos nacionais ou internacionais nem em pedidos de patente consultados no INPI e no Espacenet.",
              },
              references: [frascati("§2.15")],
            },
            {
              id: "ev-3",
              title: "Busca de anterioridade sem método descrito",
              polarity: "negative",
              explanation:
                "A busca em bases de patentes é citada, mas sem termos, datas ou resultados. Isso enfraquece a demonstração de novidade numa eventual contestação.",
              projectExcerpt: {
                ...plan,
                page: 4,
                excerpt:
                  "Foi realizada busca de anterioridade nas principais bases de patentes.",
              },
              references: [faqMcti],
            },
          ],
        },
        {
          id: "rule-exc-04",
          code: "EXC-04",
          name: "Tecnologia de amplo domínio",
          score: 66,
          explanation:
            "Parte do projeto (comunicação LoRa e aplicativo de leitura) usa tecnologia de amplo domínio. Isso não exclui o projeto, mas essas atividades não devem ser contadas como P&D.",
          normativeSource: guiaMcti("§7 (exclusões)"),
          evidences: [
            {
              id: "ev-1",
              title: "Módulo de comunicação de prateleira",
              polarity: "negative",
              explanation:
                "A transmissão de dados usa módulo LoRa comercial sem modificação: atividade de engenharia rotineira.",
              projectExcerpt: {
                ...plan,
                page: 7,
                excerpt:
                  "A transmissão será feita por módulo LoRaWAN comercial, com firmware padrão do fabricante.",
              },
              references: [guiaMcti("§7"), frascati("§2.49")],
            },
            {
              id: "ev-2",
              title: "Escopo de P&D separado do restante",
              polarity: "positive",
              explanation:
                "O plano separa explicitamente o núcleo de pesquisa (calibração) das atividades de integração, o que facilita o enquadramento parcial.",
              projectExcerpt: {
                ...plan,
                page: 8,
                excerpt:
                  "As atividades de integração de comunicação e desenvolvimento do aplicativo não compõem o escopo de P&D deste projeto.",
              },
              references: [faqMcti],
            },
          ],
        },
      ],
    },
    {
      id: "crit-creativity",
      key: "creativity",
      name: "Criatividade",
      score: 64,
      summary:
        "Há uma hipótese original para o problema de salinidade, mas a descrição do projeto mistura a solução criativa com etapas convencionais de produto.",
      rules: [
        {
          id: "rule-proj-15",
          code: "PROJ-15",
          name: "Descrição do projeto",
          score: 68,
          explanation:
            "A descrição apresenta a hipótese central e por que ela não é óbvia para um especialista, mas dedica muito espaço a funcionalidades do aplicativo.",
          normativeSource: frascati("§2.17"),
          evidences: [
            {
              id: "ev-1",
              title: "Hipótese não óbvia formulada",
              polarity: "positive",
              explanation:
                "Usar duas frequências de excitação para separar o efeito da salinidade é uma abordagem original para dispositivos de baixo custo.",
              projectExcerpt: {
                ...plan,
                page: 5,
                excerpt:
                  "Hipótese: a leitura em duas frequências (10 kHz e 150 kHz) permite estimar e subtrair a componente resistiva associada à salinidade sem sensor dedicado.",
              },
              references: [frascati("§2.17"), guiaMcti("§6.2")],
            },
            {
              id: "ev-2",
              title: "Foco excessivo em funcionalidades de produto",
              polarity: "negative",
              explanation:
                "Metade da descrição trata de telas e notificações do aplicativo, que não são atividades de P&D e diluem o argumento.",
              projectExcerpt: {
                ...plan,
                page: 9,
                excerpt:
                  "O aplicativo terá painel com histórico, alertas por SMS e integração com assistentes de voz.",
              },
              references: [faqMcti],
            },
          ],
        },
        {
          id: "rule-exc-07",
          code: "EXC-07",
          name: "Cópia ou engenharia reversa",
          score: 58,
          explanation:
            "Um protótipo inicial partiu da desmontagem de um sensor importado. O relatório mostra divergência posterior, mas o ponto precisa estar bem documentado.",
          normativeSource: guiaMcti("§7 (exclusões)"),
          evidences: [
            {
              id: "ev-1",
              title: "Protótipo inicial baseado em produto existente",
              polarity: "negative",
              explanation:
                "Engenharia reversa não é P&D. O analista deve verificar se essa fase foi excluída dos dispêndios.",
              projectExcerpt: {
                ...report,
                page: 2,
                excerpt:
                  "Na fase 0, foi analisado o circuito do sensor importado modelo X para dimensionamento inicial da sonda.",
              },
              references: [guiaMcti("§7"), decreto5798],
            },
            {
              id: "ev-2",
              title: "Divergência técnica documentada",
              polarity: "positive",
              explanation:
                "O relatório descreve como o circuito final se afastou do produto analisado, o que afasta a hipótese de cópia.",
              projectExcerpt: {
                ...report,
                page: 6,
                excerpt:
                  "O circuito de excitação dupla foi projetado do zero; nenhum bloco do sensor de referência foi mantido na versão 3 do protótipo.",
              },
              references: [frascati("§2.17")],
            },
          ],
        },
      ],
    },
    {
      id: "crit-uncertainty",
      key: "uncertainty",
      name: "Incerteza",
      score: 72,
      summary:
        "O projeto descreve riscos técnicos e hipóteses descartadas, mas não registra resultados negativos de todos os experimentos.",
      rules: [
        {
          id: "rule-proj-13",
          code: "PROJ-13",
          name: "Barreira tecnológica",
          score: 80,
          explanation:
            "Há um problema técnico claro e as abordagens testadas estão descritas.",
          normativeSource: guiaMcti("§6.3"),
          evidences: [
            {
              id: "ev-1",
              title: "Hipótese de modelo descartada",
              polarity: "positive",
              explanation:
                "Registra uma abordagem que falhou e o motivo, o que indica incerteza real.",
              projectExcerpt: {
                ...report,
                page: 4,
                excerpt:
                  "A primeira abordagem, baseada em tabela de correção fixa, não atingiu a precisão mínima de 85% nos dados de teste de campo.",
              },
              references: [frascati("§2.18")],
            },
            {
              id: "ev-2",
              title: "Risco técnico declarado no início",
              polarity: "positive",
              explanation:
                "O plano admite que não se sabia se a precisão-alvo era alcançável com componentes de baixo custo.",
              projectExcerpt: {
                ...plan,
                page: 6,
                excerpt:
                  "Não há garantia de que a precisão de ±3% seja atingível com o conversor A/D de 12 bits previsto no orçamento.",
              },
              references: [frascati("§2.18"), guiaMcti("§6.3")],
            },
            {
              id: "ev-3",
              title: "Resultados negativos incompletos",
              polarity: "negative",
              explanation:
                "Só um dos quatro experimentos de campo tem resultado registrado. O MCTI costuma pedir o registro de todas as tentativas.",
              projectExcerpt: {
                ...report,
                page: 9,
                excerpt:
                  "Os experimentos 2, 3 e 4 seguiram o mesmo protocolo e não serão detalhados.",
              },
              references: [faqMcti],
            },
          ],
        },
        {
          id: "rule-proj-14",
          code: "PROJ-14",
          name: "Metodologia de P&D",
          score: 58,
          explanation:
            "A metodologia de pesquisa aparece só parcialmente: o documento descreve mais a gestão do projeto do que o método experimental.",
          normativeSource: frascati("§2.18"),
          evidences: [
            {
              id: "ev-1",
              title: "Metodologia descrita só como Scrum",
              polarity: "negative",
              explanation:
                "O MCTI critica descrever apenas gestão ágil em vez da metodologia de pesquisa.",
              projectExcerpt: {
                ...plan,
                page: 6,
                excerpt:
                  "O desenvolvimento seguirá sprints quinzenais com revisão ao final de cada ciclo.",
              },
              references: [faqMcti],
            },
            {
              id: "ev-2",
              title: "Protocolo de ensaio em bancada",
              polarity: "positive",
              explanation:
                "O relatório descreve amostras, variáveis controladas e critério de sucesso dos ensaios de bancada.",
              projectExcerpt: {
                ...report,
                page: 5,
                excerpt:
                  "Foram preparadas 40 amostras de solo com 5 níveis de salinidade e 8 de umidade; o critério de aceitação é erro absoluto médio inferior a 3%.",
              },
              references: [frascati("§2.18")],
            },
          ],
        },
      ],
    },
    {
      id: "crit-systematic",
      key: "systematic",
      name: "Sistematização",
      score: 55,
      summary:
        "Existe cronograma e orçamento, mas o projeto não aparece como unidade única ao longo dos anos e há lacunas no registro de horas.",
      rules: [
        {
          id: "rule-proj-16",
          code: "PROJ-16",
          name: "Datas e evolução anual",
          score: 62,
          explanation:
            "Datas de início e fim estão claras, mas a evolução de 2025 para 2026 não é descrita no mesmo nível de detalhe.",
          normativeSource: inRfb1187,
          evidences: [
            {
              id: "ev-1",
              title: "Cronograma com marcos técnicos",
              polarity: "positive",
              explanation:
                "O cronograma vincula entregas a marcos técnicos (protótipo v1, v2, v3), e não só a datas.",
              projectExcerpt: {
                ...schedule,
                page: 1,
                excerpt:
                  "Marco M2 (jun/2025): protótipo v2 com excitação dupla validado em bancada.",
              },
              references: [frascati("§2.19"), inRfb1187],
            },
            {
              id: "ev-2",
              title: "Ano de 2026 sem relatório de evolução",
              polarity: "negative",
              explanation:
                "Projetos plurianuais precisam mostrar o que foi feito em cada ano-base.",
              projectExcerpt: {
                ...schedule,
                page: 3,
                excerpt: "2026: continuidade das atividades.",
              },
              references: [faqMcti],
            },
          ],
        },
        {
          id: "rule-proj-17",
          code: "PROJ-17",
          name: "Projeto como unidade",
          score: 46,
          explanation:
            "O orçamento mistura dispêndios do projeto de P&D com custos de produção do primeiro lote, o que dificulta tratar o projeto como unidade.",
          normativeSource: decreto5798,
          evidences: [
            {
              id: "ev-1",
              title: "Orçamento inclui lote de produção",
              polarity: "negative",
              explanation:
                "Custos de produção não são dispêndio de P&D e precisam ser separados.",
              projectExcerpt: {
                ...schedule,
                page: 2,
                excerpt:
                  "Rubrica 4: aquisição de componentes para lote piloto de 500 unidades, R$ 62.000,00.",
              },
              references: [lei11196, decreto5798],
            },
            {
              id: "ev-2",
              title: "Equipe dedicada identificada",
              polarity: "positive",
              explanation:
                "A equipe do projeto está nomeada, com função e carga horária, o que ajuda a delimitar o projeto.",
              projectExcerpt: {
                ...schedule,
                page: 2,
                excerpt:
                  "Equipe: 1 pesquisador doutor (40h), 2 engenheiros eletrônicos (40h), 1 técnico de campo (20h).",
              },
              references: [inRfb1187],
            },
            {
              id: "ev-3",
              title: "Controle de horas não mencionado",
              polarity: "negative",
              explanation:
                "Não há menção a apontamento de horas por atividade, que é a principal prova de dedicação ao projeto.",
              references: [faqMcti],
            },
          ],
        },
      ],
    },
    {
      id: "crit-transferability",
      key: "transferability",
      name: "Transferibilidade",
      score: 34,
      summary:
        "Os registros atuais não permitiriam que outro pesquisador reproduzisse os resultados: faltam dados brutos, versões de firmware e parâmetros de calibração.",
      rules: [
        {
          id: "rule-proj-14",
          code: "PROJ-14",
          name: "Metodologia de P&D (registros reproduzíveis)",
          score: 38,
          explanation:
            "O método está descrito em alto nível, mas sem os parâmetros necessários para reprodução.",
          normativeSource: frascati("§2.20"),
          evidences: [
            {
              id: "ev-1",
              title: "Dados brutos não disponibilizados",
              polarity: "negative",
              explanation:
                "O relatório apresenta só gráficos agregados; sem os dados brutos, o resultado não pode ser verificado.",
              projectExcerpt: {
                ...report,
                page: 11,
                excerpt:
                  "Os dados completos dos ensaios encontram-se em posse da equipe técnica.",
              },
              references: [frascati("§2.20")],
            },
            {
              id: "ev-2",
              title: "Parâmetros de calibração publicados",
              polarity: "positive",
              explanation:
                "Os coeficientes do modelo de compensação estão em tabela no anexo, o que permite reproduzir parte do resultado.",
              projectExcerpt: {
                ...report,
                page: 14,
                excerpt:
                  "Anexo B: coeficientes a0–a4 do modelo de compensação para cada faixa de salinidade.",
              },
              references: [frascati("§2.20")],
            },
          ],
        },
        {
          id: "rule-exc-11",
          code: "EXC-11",
          name: "Software de rotina",
          score: 30,
          explanation:
            "O firmware e o aplicativo são descritos como desenvolvimento de rotina, sem documentação técnica que permita separá-los do núcleo de pesquisa.",
          normativeSource: frascati("§2.68"),
          evidences: [
            {
              id: "ev-1",
              title: "Firmware sem versionamento",
              polarity: "negative",
              explanation:
                "Sem controle de versão do firmware, não é possível saber qual versão gerou cada resultado.",
              projectExcerpt: {
                ...report,
                page: 8,
                excerpt:
                  "O firmware foi ajustado ao longo dos ensaios conforme necessidade.",
              },
              references: [frascati("§2.68"), faqMcti],
            },
            {
              id: "ev-2",
              title: "Aplicativo descrito como CRUD",
              polarity: "negative",
              explanation:
                "Telas de cadastro e consulta são software de rotina e não devem ser incluídas como P&D.",
              projectExcerpt: {
                ...plan,
                page: 9,
                excerpt:
                  "O aplicativo permitirá cadastrar propriedades, talhões e sensores, e consultar leituras.",
              },
              references: [frascati("§2.68")],
            },
          ],
        },
      ],
    },
  ],
};
