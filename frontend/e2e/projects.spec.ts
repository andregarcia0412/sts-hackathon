import { USERS, expect, signInAs, test } from "./fixtures.ts";

test.beforeEach(async ({ page }) => {
  await signInAs(page, USERS.ana);
  await page.goto("/projetos");
  await expect(page.locator("tbody tr").first()).toBeVisible();
});

test("card de status filtra e o total bate com a paginação", async ({ page }) => {
  const tile = page.getByRole("button", { name: /Decididos/ });
  const count = Number((await tile.textContent())?.match(/\d+/)?.[0]);
  await tile.click();
  await expect(page).toHaveURL(/status=decided/);
  await expect(page.getByText(/Mostrando/)).toContainText(`de ${count}`);
  await expect(page.locator("tbody").getByText("Sem decisão")).toHaveCount(0);
});

test("decisão filtra a lista e o botão de filtro limpa", async ({ page }) => {
  await page.getByLabel("Decisão").selectOption("with_reservations");
  await expect(page).toHaveURL(/decisao=with_reservations/);
  await expect
    .poll(async () => {
      const decisions = await page.locator("tbody td:nth-child(5)").allTextContents();
      return decisions.length > 0 && decisions.every((t) => t.includes("Com ressalvas"));
    })
    .toBe(true);
  await page.getByRole("button", { name: "Limpar 1 filtro" }).click();
  await expect(page).not.toHaveURL(/decisao=/);
});

test("busca filtra por nome ou empresa", async ({ page }) => {
  await page.getByRole("searchbox").pressSequentially("caju", { delay: 15 });
  await expect(page).toHaveURL(/q=caju/);
  const rows = page.locator("tbody tr");
  await expect
    .poll(async () => {
      const texts = await rows.allTextContents();
      return texts.length > 0 && texts.every((t) => t.toLowerCase().includes("caju"));
    })
    .toBe(true);
});

test("critério mais fraco + ordenação", async ({ page }) => {
  await page.getByLabel("Força da evidência do critério mais fraco").selectOption("weak");
  await page.getByLabel("Ordenar por").selectOption("weakest");
  await expect(page).toHaveURL(/ordem=weakest/);
  await expect(page).toHaveURL(/banda=weak/);
  await expect
    .poll(async () => {
      const weakest = await page.locator("tbody td:nth-child(4)").allTextContents();
      return weakest.length > 0 && weakest.every((t) => /Não (demonstrad|documentad|investigad)/.test(t));
    })
    .toBe(true);
});

test("período de envio", async ({ page }) => {
  await page.getByRole("button", { name: "Data de envio" }).click();
  await page.getByLabel("Enviado a partir de").fill("2026-09-01");
  await page.getByLabel("Enviado até").fill("2026-09-30");
  await expect(page).toHaveURL(/ate=2026-09-30/);
  // The submission date is in each row's info line ("enviado em …")
  await expect
    .poll(async () => {
      const rows = await page.locator("tbody td:nth-child(1)").allTextContents();
      return rows.length > 0 && rows.every((r) => /enviado em \d{2}\/09\/2026/.test(r));
    })
    .toBe(true);
});

test("paginação e botão voltar", async ({ page }) => {
  const first = await page.locator("tbody tr").first().textContent();
  await page.getByRole("button", { name: "Próxima página" }).click();
  await expect(page).toHaveURL(/pagina=2/);
  await expect(page.locator("tbody tr").first()).not.toHaveText(first ?? "");
  await page.goBack();
  await expect(page).not.toHaveURL(/pagina=2/);
});

test("upload recusa formato não aceito", async ({ page }) => {
  await page.getByRole("button", { name: "Novo projeto" }).first().click();
  await page.getByLabel("Selecionar arquivos").setInputFiles({
    name: "foto.png",
    mimeType: "image/png",
    buffer: Buffer.from("x"),
  });
  await expect(page.getByText(/formato não aceito/)).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("heading", { name: "Novo projeto" })).toBeHidden();
});

test("clicar num resultado logo depois de digitar não volta para a lista", async ({ page }) => {
  // Regression: the debounced search fired after the click and pulled the analyst back
  await page.goto("/projetos?q=senso");
  const row = page.getByRole("row", { name: /Sensor de umidade/ });
  await expect(row).toBeVisible();
  await page.getByRole("searchbox").press("r");
  await row.getByRole("link", { name: "Abrir análise" }).click();
  await expect(page).toHaveURL(/\/projetos\/p1\/analise/);
  await page.waitForTimeout(600);
  await expect(page).toHaveURL(/\/projetos\/p1\/analise/);
});
