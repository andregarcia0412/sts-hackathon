import { USERS, expect, signInAs, test } from "./fixtures.ts";

test("rota protegida leva ao login e depois de volta", async ({ page }) => {
  await page.goto("/projetos/p1/decisao");
  await expect(page).toHaveURL(/\/login\?next=/);
  await page.getByLabel("E-mail").fill(USERS.ana.email);
  await page.getByLabel("Senha").fill("qualquer");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page).toHaveURL(/\/projetos\/p1\/decisao$/);
});

test("e-mail desconhecido mostra erro", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("E-mail").fill("ninguem@exemplo.com");
  await page.getByLabel("Senha").fill("x");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText("E-mail ou senha inválidos");
});

test("next externo é ignorado (sem redirecionamento aberto)", async ({ page }) => {
  await page.goto("/login?next=//exemplo-malicioso.com");
  await page.getByRole("button", { name: /Bruno Carvalho/ }).click();
  await expect(page).toHaveURL(/\/projetos$/);
});

test("logado, /login redireciona e Sair volta ao login", async ({ page }) => {
  await signInAs(page, USERS.ana);
  await page.goto("/login");
  await expect(page).toHaveURL(/\/projetos$/);
  await page.getByRole("button", { name: "Sair" }).click();
  // Keeps where the analyst was, to come back after signing in again
  await expect(page).toHaveURL(/\/login\?next=%2Fprojetos$/);
  await expect(page.getByRole("heading", { name: "Entrar" })).toBeVisible();
});

test("cada analista vê só os próprios projetos", async ({ page }) => {
  await signInAs(page, USERS.bruno);
  await page.goto("/projetos?q=Sensor%20de%20umidade");
  await expect(page.getByText("Nenhum projeto com esses filtros")).toBeVisible();
});
