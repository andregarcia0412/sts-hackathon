import { USERS, expect, signInAs, test } from "./fixtures.ts";

test.beforeEach(async ({ page }) => {
  await signInAs(page, USERS.ana);
});

test("projeto decidido mostra a decisão vigente e links para o grafo", async ({ page }) => {
  await page.goto("/projetos/p2/decisao");
  await expect(page.getByText("decisão vigente", { exact: true })).toBeVisible();
  await expect(page.locator('[aria-current="step"]')).toHaveText("Documento de decisão");
  const href = await page.getByRole("link", { name: /Ver .* no grafo/ }).first().getAttribute("href");
  expect(href).toMatch(/\/analise\?.*no=/);
});

test("nova decisão vai para o topo da trilha e aparece na lista", async ({ page }) => {
  await page.goto("/projetos/p2/decisao");
  await page.getByText("Precisa de revisão", { exact: true }).first().click();
  await page.getByLabel(/^Justificativa/).fill("Revisar a transferibilidade.");
  await page.getByRole("button", { name: "Registrar decisão" }).click();
  const latest = page.locator("#trilha ol > li").first();
  await expect(latest).toContainText("Precisa de revisão");
  await expect(latest.getByText("decisão vigente", { exact: true })).toBeVisible();
  await expect(page.getByText(/Decisão vigente: Precisa de revisão/)).toBeVisible();
  await page.goto("/projetos?decisao=needs_review");
  await expect(page.locator("tbody")).toContainText("Precisa de revisão");
});

test("projeto gerado: decisão é salva (cópia na escrita) e sobrevive ao reload", async ({ page }) => {
  // Any generated project (id g…) that is ready for analysis
  await page.goto("/projetos?status=ready&ordem=oldest");
  const href = await page.locator('tbody a[href^="/projetos/g"][href$="/analise"]').first().getAttribute("href");
  await page.goto(href!.replace("/analise", "/decisao"));
  await page.getByText("Enquadrável", { exact: true }).first().click();
  await page.getByLabel(/^Justificativa/).fill("Teste de projeto gerado.");
  await page.getByRole("button", { name: "Registrar decisão" }).click();
  await expect(page.locator("#trilha")).toContainText("Teste de projeto gerado.");
  await page.reload();
  await expect(page.locator("#trilha")).toContainText("Teste de projeto gerado.");
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
