import { USERS, chooseOption, expect, signInAs, test } from "./fixtures.ts";

test.beforeEach(async ({ page }) => {
  await signInAs(page, USERS.ana);
});

test("visão Critério mostra um critério inteiro dentro da tela", async ({ page }) => {
  await page.goto("/projetos/p1/analise");
  await expect(page.locator(".react-flow__node-criterion")).toHaveCount(1);
  await expect(page.locator(".react-flow__node-rule")).toHaveCount(2);
  await expect(page.locator(".react-flow__node-evidence")).toHaveCount(5);
  await page.waitForTimeout(600); // camera animation
  const pane = await page.locator(".react-flow").boundingBox();
  const boxes = await page
    .locator(".react-flow__node")
    .evaluateAll((nodes) => nodes.map((n) => n.getBoundingClientRect().toJSON()));
  for (const box of boxes) {
    expect(box.left).toBeGreaterThanOrEqual(pane!.x - 1);
    expect(box.right).toBeLessThanOrEqual(pane!.x + pane!.width + 1);
  }
});

test("seleção na URL: painel, árvore e botão voltar", async ({ page }) => {
  await page.goto("/projetos/p1/analise");
  await page.getByRole("button", { name: /Incerteza/ }).click();
  await expect(page).toHaveURL(/no=crit-uncertainty/);
  // The new criterion comes in while the previous one fades out
  await expect(page.locator(".react-flow__node-criterion", { hasText: "Incerteza" })).toBeVisible();
  await expect(page.locator(".react-flow__node-criterion")).toHaveCount(1);
  await page.locator(".react-flow__node-rule").first().click();
  await expect(page.getByRole("form", { name: "Decisão do analista" })).toBeVisible();
  await page.locator(".react-flow__node-evidence").first().click();
  await expect(page.getByText("Impacto na nota da regra").first()).toBeVisible();
  await page.goBack();
  await expect(page).toHaveURL(/no=crit-uncertainty\.rule-[^.&]+$/);
});

test("trocar de método muda a árvore", async ({ page }) => {
  await page.goto("/projetos/p1/analise");
  await page.getByRole("button", { name: "Formulário MCTI" }).click();
  await expect(page).toHaveURL(/metodo=mcti_form/);
  await expect(page.getByText("Barreira tecnológica").first()).toBeVisible();
});

test("nota da regra exige justificativa e persiste após recarregar", async ({ page }) => {
  await page.goto("/projetos/p1/analise?no=crit-novelty.rule-proj-12");
  await page.getByRole("button", { name: "Confirmar nota da regra" }).click();
  await expect(page.getByText(/justificativa é obrigatória/)).toBeVisible();
  await chooseOption(page, "Nota da regra", /^Sustentado/);
  await page.getByLabel(/Justificativa/).fill("Evidência 1.1.1 é direta.");
  await page.getByRole("button", { name: "Confirmar nota da regra" }).click();
  await expect(page.getByText("Registrada:")).toBeVisible();
  await page.reload();
  await expect(page.getByText("Registrada:")).toBeVisible();
});

test("descartar evidência pede motivo; confirmar depois fica na trilha", async ({ page }) => {
  await page.goto("/projetos/p1/analise?no=crit-novelty.rule-proj-12");
  const card = page.getByRole("article", { name: "Evidência 1.1.1" });
  await card.getByRole("button", { name: "Descartar" }).click();
  await expect(page.getByRole("button", { name: "Descartar evidência" })).toBeDisabled();
  await page.getByLabel(/Por que descartar/).fill("Fala de outro módulo.");
  await page.getByRole("button", { name: "Descartar evidência" }).click();
  await expect(card.getByText("Descartada")).toBeVisible();
  await card.getByRole("button", { name: "Confirmar" }).click();
  await expect(card.getByText("Confirmada")).toBeVisible();
});

test("regra contraditória mostra o alerta", async ({ page }) => {
  await page.goto("/projetos/p1/analise?no=crit-systematic.rule-proj-17");
  await expect(page.getByText(/apontam em sentidos opostos/)).toBeVisible();
});

test("chat: fechar com Esc depois de limpar a conversa", async ({ page }) => {
  await page.goto("/projetos/p1/analise");
  await page.getByRole("button", { name: "Abrir assistente da análise" }).click();
  const chat = page.getByRole("dialog", { name: "Assistente da análise" });
  await chat.getByRole("list", { name: "Sugestões" }).getByRole("button").first().click();
  await expect(chat.getByText("Fontes")).toBeVisible();
  await chat.getByRole("button", { name: "Limpar conversa" }).click();
  await page.keyboard.press("Escape");
  await expect(chat).toBeHidden();
});

test("estados: processando, erro, inexistente e ?no= inválido", async ({ page }) => {
  await page.goto("/projetos/p3/analise");
  await expect(page.getByText(/ainda em processamento/)).toBeVisible();
  await page.goto("/projetos/p4/analise");
  await expect(page.getByText(/Não foi possível processar/)).toBeVisible();
  await page.goto("/projetos/nao-existe/analise");
  await expect(page.getByText("Projeto não encontrado")).toBeVisible();
  await page.goto("/projetos/p1/analise?no=lixo.qualquer");
  await expect(page.locator(".react-flow__node-criterion")).toHaveCount(1);
});
