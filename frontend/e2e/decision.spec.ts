import { USERS, expect, signInAs, test } from "./fixtures.ts";

test.beforeEach(async ({ page }) => {
  await signInAs(page, USERS.ana);
});

test("projeto decidido mostra a decisão vigente e links para a árvore", async ({ page }) => {
  await page.goto("/projetos/p2/decisao");
  await expect(page.getByText("decisão vigente", { exact: true })).toBeVisible();
  await expect(page.locator('[aria-current="step"]')).toHaveText("Documento de decisão");
  const href = await page.getByRole("link", { name: /Ver .* na árvore/ }).first().getAttribute("href");
  expect(href).toMatch(/\/analise\?.*no=/);
});

test("nova decisão vai para o topo da trilha e aparece na lista", async ({ page }) => {
  await page.goto("/projetos/p2/decisao");
  await page.getByText("Com ressalvas", { exact: true }).first().click();
  await page.getByLabel(/^Justificativa/).fill("Revisar a transferibilidade.");
  await page.getByRole("button", { name: "Registrar decisão" }).click();
  const latest = page.locator("#trilha ol > li").first();
  await expect(latest).toContainText("Com ressalvas");
  await expect(latest.getByText("decisão vigente", { exact: true })).toBeVisible();
  await expect(page.getByText(/Decisão vigente: Com ressalvas/)).toBeVisible();
  await page.goto("/projetos?decisao=with_reservations");
  await expect(page.locator("tbody")).toContainText("Com ressalvas");
});

test("projeto gerado: decisão é salva (cópia na escrita) e sobrevive ao reload", async ({ page }) => {
  // Any generated project (id g…) that is ready for analysis
  await page.goto("/projetos?status=ready&ordem=oldest");
  const href = await page.locator('tbody a[href^="/projetos/g"][href$="/analise"]').first().getAttribute("href");
  await page.goto(href!.replace("/analise", "/decisao"));
  await page.getByText("Elegível", { exact: true }).first().click();
  await page.getByLabel(/^Justificativa/).fill("Teste de projeto gerado.");
  await page.getByRole("button", { name: "Registrar decisão" }).click();
  await expect(page.locator("#trilha")).toContainText("Teste de projeto gerado.");
  await page.reload();
  await expect(page.locator("#trilha")).toContainText("Teste de projeto gerado.");
});

test("evidência insuficiente é uma classificação e filtra a lista", async ({ page }) => {
  await page.goto("/projetos/p2/decisao");
  await page.getByText("Evidência insuficiente", { exact: true }).first().click();
  await page.getByLabel(/^Justificativa/).fill("Faltam os registros de calibração: solicitar à equipe.");
  await page.getByRole("button", { name: "Registrar decisão" }).click();
  await expect(page.locator("#trilha ol > li").first()).toContainText("Evidência insuficiente");
  await page.goto("/projetos?decisao=insufficient_evidence");
  await expect(page.getByLabel("Decisão", { exact: true })).toHaveValue("insufficient_evidence");
  await expect(page.locator("tbody")).toContainText("Evidência insuficiente");
});

test("documento alterna o método e abre o item pela URL", async ({ page }) => {
  await page.goto("/projetos/p1/decisao");
  await expect(page.getByRole("heading", { name: "Detalhamento · Frascati" })).toBeVisible();
  await page.getByRole("group", { name: "Método do documento" }).getByRole("button", { name: "Formulário MCTI" }).click();
  await expect(page.getByRole("heading", { name: "Detalhamento · Formulário MCTI" })).toBeVisible();
  // A pendency opens its rule in the details
  await page.locator("#pendencias li button").first().click();
  await expect(page).toHaveURL(/no=/);
  await expect(page.locator('#detalhamento button[aria-expanded="true"]')).toHaveCount(2);
});

test("análise em processamento não tem documento", async ({ page }) => {
  await page.goto("/projetos/p3/decisao");
  await expect(page.getByText(/ainda não está pronta/)).toBeVisible();
});

test("nenhuma tela tem rolagem horizontal no celular", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  for (const path of ["/projetos", "/projetos/p1/analise?no=crit-novelty.rule-proj-12", "/projetos/p1/decisao"]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow, path).toBeLessThanOrEqual(0);
  }
});
