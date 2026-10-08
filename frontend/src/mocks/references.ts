import type { Reference } from "@/domain/types";

const FRASCATI_URL =
  "https://www.oecd.org/en/publications/2015/10/frascati-manual-2015_g1g57dcb.html";

export const frascati = (section: string): Reference => ({
  label: `Manual de Frascati ${section}`,
  url: FRASCATI_URL,
});

export const guiaMcti = (section: string): Reference => ({
  label: `Guia Prático da Lei do Bem (MCTI) ${section}`,
});

export const faqMcti: Reference = {
  label: "Perguntas frequentes da Lei do Bem (MCTI)",
  url: "https://www.gov.br/mcti/pt-br/acompanhe-o-mcti/lei-do-bem/paginas/perguntas-frequentes",
};

export const lei11196: Reference = {
  label: "Lei nº 11.196/2005, art. 17",
  url: "https://www.planalto.gov.br/ccivil_03/_ato2004-2006/2005/lei/l11196.htm",
};

export const decreto5798: Reference = {
  label: "Decreto nº 5.798/2006, art. 2º",
  url: "https://www.planalto.gov.br/ccivil_03/_ato2004-2006/2006/decreto/d5798.htm",
};

export const inRfb1187: Reference = {
  label: "IN RFB nº 1.187/2011, art. 3º",
};
