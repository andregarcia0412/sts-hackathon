import { USERS, chooseOption, combobox, expect, signInAs, test, typeLikeAPerson } from "./fixtures.ts";

// Journeys type like a person and walk through several screens: give them time
test.describe.configure({ timeout: 120_000 });

/*
 * User journeys, written the way a person would test the app by hand: only
 * what is visible on screen (labels, buttons, text), no deep links to skip
 * steps. Each journey starts from a fresh session and fresh mock data.
 */

test("analista faz a primeira análise, decide e gera o documento", async ({ page }) => {
  await test.step("entra pelo atalho de demonstração", async () => {
    await page.goto("/");
    await page.getByRole("button", { name: /Ana Ribeiro/ }).click();
    await expect(page.getByRole("heading", { name: "Meus projetos" })).toBeVisible();
  });

  await test.step("procura o projeto e abre a análise", async () => {
    await typeLikeAPerson(page.getByRole("searchbox"), "sensor");
    const row = page.getByRole("row", { name: /Sensor de umidade/ });
    await row.getByRole("link", { name: "Abrir análise" }).click();
    await expect(page.getByRole("heading", { name: "Detalhamento de informações" })).toBeVisible();
    await expect(page.locator(".react-flow__node-criterion")).toHaveCount(1);
  });

  await test.step("lê como a nota do critério foi formada", async () => {
    await page.getByText("Como a nota foi formada").first().click();
    await expect(page.getByRole("list", { name: /Composição da nota/ }).first()).toBeVisible();
  });

  await test.step("abre a regra 1.1 e confirma a primeira evidência", async () => {
    await page.getByRole("button", { name: /^1\.1 / }).first().click();
    const evidence = page.getByRole("article", { name: "Evidência 1.1.1" });
    await evidence.getByRole("button", { name: "Confirmar" }).click();
    await expect(evidence.getByText("Confirmada")).toBeVisible();
  });

  await test.step("dá nota à regra 1.1", async () => {
    await chooseOption(page, "Nota da regra", /^Sustentado/);
    await typeLikeAPerson(page.getByLabel(/Justificativa/), "A comparação com o estado da arte (1.1.1) é direta.");
    await page.getByRole("button", { name: "Confirmar nota da regra" }).click();
    await expect(page.getByText("Registrada:")).toBeVisible();
  });

  await test.step("vai para a regra 1.2 pela árvore e dá nota", async () => {
    await page.locator(".react-flow__node-rule", { hasText: "Tecnologia de amplo domínio" }).click();
    const dock = page.getByRole("form", { name: "Decisão do analista" });
    await expect(dock.getByText("Regra 1.2", { exact: true })).toBeVisible();
    await chooseOption(page, "Nota da regra", /^Parcialmente sustentado/);
    await typeLikeAPerson(page.getByLabel(/Justificativa/), "Parte da solução usa tecnologia de amplo domínio.");
    await page.getByRole("button", { name: "Confirmar nota da regra" }).click();
    await expect(page.getByText("Registrada:")).toBeVisible();
    await expect(page.getByText("1 de 5 critérios decididos pelo analista")).toBeVisible();
  });

  await test.step("gera o documento e encontra a nota dada", async () => {
    await page.getByRole("link", { name: "Gerar documento de decisão" }).click();
    await expect(page.getByRole("heading", { name: "Resumo" })).toBeVisible();
    // Opens at the rule that was selected in the tree (1.2), with its note
    const details = page.locator("#detalhamento");
    await expect(details.getByText("Parte da solução usa tecnologia de amplo domínio.")).toBeVisible();
    await details.getByRole("button", { name: /^1\.1 / }).click();
    await expect(details.getByText("A comparação com o estado da arte (1.1.1) é direta.")).toBeVisible();
  });

  await test.step("registra a decisão final", async () => {
    await page
      .getByRole("navigation", { name: "Seções do documento" })
      .getByRole("button", { name: "Decisão do analista" })
      .click();
    await page.getByRole("button", { name: "Registrar decisão" }).click();
    await expect(page.getByText("Escolha uma classificação.")).toBeVisible();
    await page.getByText("Com ressalvas", { exact: true }).click();
    await typeLikeAPerson(page.getByLabel(/^Justificativa/), "Transferibilidade fraca: pedir registros reproduzíveis.");
    await page.getByRole("button", { name: "Registrar decisão" }).click();
    const latest = page.locator("#trilha ol > li").first();
    await expect(latest).toContainText("Com ressalvas");
    await expect(latest.getByText("decisão vigente", { exact: true })).toBeVisible();
  });

  await test.step("exporta o PDF", async () => {
    // The browser's print dialog cannot be driven: count the calls instead
    await page.evaluate(() => {
      (window as unknown as { printCalls: number }).printCalls = 0;
      window.print = () => {
        (window as unknown as { printCalls: number }).printCalls++;
      };
    });
    await page.getByRole("button", { name: "Baixar documento" }).click();
  });

  await test.step("volta para a lista e vê o projeto decidido", async () => {
    await page.getByRole("link", { name: "Projetos" }).click();
    await typeLikeAPerson(page.getByRole("searchbox"), "sensor");
    await expect(page.getByRole("row", { name: /Sensor de umidade/ }).getByText("Decidido")).toBeVisible();
  });
});

test("analista discorda do modelo, contesta e vê a reanálise na trilha", async ({ page }) => {
  await test.step("entra pelo formulário de login", async () => {
    await page.goto("/login");
    await typeLikeAPerson(page.getByLabel("Email"), USERS.ana.email);
    await typeLikeAPerson(page.getByLabel("Senha", { exact: true }), "123");
    await page.keyboard.press("Enter");
    await expect(page.getByRole("heading", { name: "Meus projetos" })).toBeVisible();
  });

  await test.step("abre o critério mais fraco do projeto", async () => {
    await typeLikeAPerson(page.getByRole("searchbox"), "sensor");
    await page.getByRole("row", { name: /Sensor de umidade/ }).getByRole("link", { name: "Abrir análise" }).click();
    await page.getByRole("button", { name: /Transferibilidade/ }).click();
    await page.getByRole("button", { name: /^5\.1 / }).click();
    await expect(page.getByText(/Força da evidência/).first()).toBeVisible();
  });

  await test.step("questiona a regra e argumenta no chat", async () => {
    await page.getByRole("button", { name: "Questionar regra" }).click();
    const chat = page.getByRole("dialog", { name: "Assistente da análise" });
    await expect(chat.getByText(/Contestando/).first()).toBeVisible();
    await typeLikeAPerson(
      chat.getByLabel("Seu argumento"),
      "Acho a nota baixa demais: o Relatório Técnico, p. 9, traz o protocolo de ensaio completo.",
    );
    await page.keyboard.press("Enter");
    await chat.getByRole("button", { name: "Registrar contestação" }).click();
    await chat.getByRole("button", { name: "Registrar", exact: true }).click();
  });

  await test.step("pede a reanálise", async () => {
    const chat = page.getByRole("dialog", { name: "Assistente da análise" });
    await chat.getByRole("button", { name: "Reanalisar agora" }).click();
    await expect(chat.getByText(/Reanálise concluída/)).toBeVisible({ timeout: 6000 });
    await chat.getByRole("button", { name: "Fechar assistente" }).click();
    await expect(page.getByText("Contestações (1)")).toBeVisible();
  });

  await test.step("encontra a reanálise na trilha do documento", async () => {
    await page.getByRole("link", { name: "Gerar documento de decisão" }).click();
    await page
      .getByRole("navigation", { name: "Seções do documento" })
      .getByRole("button", { name: "Trilha de decisão" })
      .click();
    await expect(page.locator("#trilha").getByText("Reanálise do modelo")).toBeVisible();
  });
});

test("analista envia um projeto novo e abre a análise quando fica pronta", async ({ page }) => {
  await signInAs(page, USERS.bruno);
  await page.goto("/projetos");

  await test.step("abre o upload pela etapa do cabeçalho", async () => {
    await page.getByRole("link", { name: "Upload de arquivos" }).click();
    await expect(page.getByRole("heading", { name: "Novo projeto" })).toBeVisible();
  });

  await test.step("vazio, não dá para enviar e o rodapé diz o que falta", async () => {
    for (const button of await page.getByRole("button", { name: "Enviar para análise" }).all()) {
      await expect(button).toBeDisabled();
    }
    await expect(page.getByText(/Preencha o nome do projeto e anexe um documento/)).toBeVisible();
  });

  await test.step("preenche, anexa, remove um arquivo e envia", async () => {
    await typeLikeAPerson(page.getByLabel(/Nome do projeto/), "Irrigação por gotejamento inteligente");
    await typeLikeAPerson(page.getByLabel(/Equipe ou empresa/), "Água Viva (fictícia)");
    await page.getByLabel("Selecionar arquivos").setInputFiles([
      { name: "plano.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF teste") },
      {
        name: "relatorio.docx",
        mimeType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        buffer: Buffer.from("docx"),
      },
    ]);
    await page.getByRole("button", { name: "Remover relatorio.docx" }).click();
    await expect(page.getByText("relatorio.docx")).toHaveCount(0);
    await expect(page.getByText("Tudo pronto para enviar.")).toBeVisible();
    await page.getByRole("button", { name: "Enviar para análise" }).last().click();
    await expect(page.getByRole("heading", { name: "Meus Projetos" })).toBeVisible();
  });

  await test.step("acompanha o processamento até ficar pronto", async () => {
    const row = page.getByRole("row", { name: /Irrigação por gotejamento/ });
    await expect(row.getByText("Processando")).toBeVisible();
    await expect(row.getByText("Em análise")).toBeVisible({ timeout: 15_000 });
    await row.getByRole("link", { name: "Abrir análise" }).click();
    await expect(page.locator(".react-flow__node").first()).toBeVisible();
  });
});

test("analista faz a triagem da fila com filtros e volta pelo navegador", async ({ page }) => {
  await signInAs(page, USERS.carla);
  await page.goto("/projetos");

  await test.step("filtra pelos cards e pelo critério mais fraco", async () => {
    await page.getByRole("button", { name: /Em análise/ }).click();
    await chooseOption(page, "Força da evidência do critério mais fraco", "Mais fraco: evidência fraca");
    await chooseOption(page, "Ordenar por", "Mais fraco primeiro");
    await expect(page).toHaveURL(/status=ready/);
    await expect(page).toHaveURL(/banda=weak/);
    const weakest = page.locator("tbody td:nth-child(4)");
    await expect(weakest.first()).toContainText(/Não (demonstrad|documentad|investigad)/);
  });

  await test.step("abre a análise e volta: os filtros continuam lá", async () => {
    await page.getByRole("link", { name: "Abrir análise" }).first().click();
    await expect(page.locator(".react-flow__node").first()).toBeVisible();
    await page.goBack();
    await expect(combobox(page, "Força da evidência do critério mais fraco")).toContainText("Mais fraco: evidência fraca");
  });

  await test.step("limpa os filtros", async () => {
    await page.getByRole("button", { name: /Limpar/ }).click();
    await expect(combobox(page, "Força da evidência do critério mais fraco")).toContainText("Critério mais fraco");
  });
});

test("analista explora o mapa geral com o mouse", async ({ page }) => {
  await signInAs(page, USERS.ana);
  await page.goto("/projetos");
  await page.getByRole("button", { name: /Em análise/ }).click();
  await page.getByRole("link", { name: "Abrir análise" }).first().click();
  await expect(page.locator(".react-flow__node").first()).toBeVisible();

  await test.step("abre o mapa geral: expande tudo e recolhe para os 5 critérios", async () => {
    await page.getByRole("button", { name: "Mapa geral" }).click();
    await expect(page.locator(".react-flow__node-criterion")).toHaveCount(5);
    await expect(page.locator(".react-flow__node-evidence").first()).toBeVisible();
    await expect(page.locator(".react-flow__node-evidence")).toHaveCount(0, { timeout: 5000 });
  });

  await test.step("clica num critério, numa regra e numa evidência", async () => {
    await page.locator(".react-flow__node-criterion").nth(2).click();
    await page.locator(".react-flow__node-rule").first().click();
    await page.locator(".react-flow__node-evidence").first().click();
    await expect(page).toHaveURL(/\.ev-/);
  });

  await test.step("usa o zoom, enquadra e arrasta a árvore", async () => {
    await page.getByRole("button", { name: "Afastar" }).click();
    await page.getByRole("button", { name: "Enquadrar a árvore inteira" }).click();
    const pane = await page.locator(".react-flow__pane").boundingBox();
    if (!pane) throw new Error("graph pane not found");
    await page.mouse.move(pane.x + 300, pane.y + 300);
    await page.mouse.down();
    await page.mouse.move(pane.x + 450, pane.y + 380, { steps: 8 });
    await page.mouse.up();
  });

  await test.step("volta para a visão de um critério", async () => {
    await page.getByRole("button", { name: "Critério", exact: true }).click();
    await expect(page.locator(".react-flow__node-criterion")).toHaveCount(1);
  });
});

test("analista usa só o teclado", async ({ page }) => {
  await test.step("faz login com Tab e Enter", async () => {
    await page.goto("/login");
    await page.getByLabel("Email").focus();
    await page.keyboard.type(USERS.ana.email);
    await page.keyboard.press("Tab");
    await page.keyboard.type("x");
    await page.keyboard.press("Enter");
    await expect(page.getByRole("heading", { name: "Meus projetos" })).toBeVisible();
  });

  await test.step("filtra 'Em análise' pelo card com o teclado", async () => {
    let reached = false;
    for (let i = 0; i < 30 && !reached; i++) {
      await page.keyboard.press("Tab");
      reached = await page.evaluate(() => document.activeElement?.textContent?.startsWith("Em análise") ?? false);
    }
    expect(reached).toBe(true);
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/status=ready/);
    // The previous (unfiltered) page stays on screen while the filtered one loads
    await expect(page.getByText(/^Mostrando 1–\d+ de 48/)).toBeVisible();
  });

  await test.step("chega ao primeiro 'Abrir análise' com Tab", async () => {
    let reached = false;
    for (let i = 0; i < 80 && !reached; i++) {
      await page.keyboard.press("Tab");
      reached = await page.evaluate(
        () => document.activeElement?.tagName === "A" && document.activeElement.textContent?.includes("Abrir análise"),
      );
    }
    expect(reached).toBe(true);
    await page.keyboard.press("Enter");
    await expect(page.locator(".react-flow__node").first()).toBeVisible();
  });

  await test.step("abre a regra 1.2 com Enter e o foco continua nela", async () => {
    let reached = false;
    for (let i = 0; i < 40 && !reached; i++) {
      await page.keyboard.press("Tab");
      reached = await page.evaluate(() => /^\s*1\.2/.test(document.activeElement?.textContent ?? ""));
    }
    expect(reached).toBe(true);
    await page.keyboard.press("Enter");
    await expect(page.getByRole("button", { name: "Confirmar nota da regra" })).toBeVisible();
    const focused = await page.evaluate(() => document.activeElement?.tagName);
    expect(focused).toBe("BUTTON");
  });
});

test.describe("no celular", () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

  test("analista dá nota a uma regra e consulta a árvore e o chat", async ({ page }) => {
    await test.step("entra e abre um projeto", async () => {
      await page.goto("/");
      await page.getByRole("button", { name: /Ana Ribeiro/ }).click();
      await page.getByRole("button", { name: /Em análise/ }).click();
      await page.getByRole("link", { name: "Abrir análise" }).first().click();
      await expect(page.locator(".react-flow__node").first()).toBeVisible();
    });

    await test.step("a etapa atual aparece no topo", async () => {
      const step = await page.locator('[aria-current="step"]').boundingBox();
      expect(step && step.x >= 0 && step.x + step.width <= 390).toBe(true);
    });

    await test.step("o botão do chat não esconde o Confirmar depois de rolar", async () => {
      await page.getByRole("button", { name: /^1\.1 / }).first().click();
      const confirm = page.getByRole("button", { name: "Confirmar nota da regra" });
      await confirm.scrollIntoViewIfNeeded();
      await page.evaluate(() => document.querySelector("main")?.scrollBy(0, 160));
      const button = await confirm.boundingBox();
      const chat = await page.getByRole("button", { name: "Abrir assistente da análise" }).boundingBox();
      if (!button || !chat) throw new Error("buttons not found");
      const overlaps =
        button.x < chat.x + chat.width && chat.x < button.x + button.width &&
        button.y < chat.y + chat.height && chat.y < button.y + button.height;
      expect(overlaps).toBe(false);
    });

    await test.step("a árvore aparece abaixo do painel", async () => {
      const graph = page.getByRole("region", { name: "Árvore de evidências" });
      await graph.scrollIntoViewIfNeeded();
      expect((await graph.boundingBox())?.height ?? 0).toBeGreaterThan(400);
    });

    await test.step("abre o chat", async () => {
      await page.getByRole("button", { name: "Abrir assistente da análise" }).click();
      await expect(page.getByRole("dialog", { name: "Assistente da análise" })).toBeVisible();
    });
  });
});
