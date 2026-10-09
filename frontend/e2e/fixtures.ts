import { test as base, expect } from "@playwright/test";
import type { Locator, Page } from "@playwright/test";

/* Demo analysts (src/mocks/users.ts) */
export const USERS = {
  ana: { id: "u1", name: "Ana Ribeiro", email: "ana.ribeiro@exemplo.com" },
  bruno: { id: "u2", name: "Bruno Carvalho", email: "bruno.carvalho@exemplo.com" },
  carla: { id: "u3", name: "Carla Mendes", email: "carla.mendes@exemplo.com" },
} as const;

type User = (typeof USERS)[keyof typeof USERS];

/** Starts the session without going through the login screen */
export const signInAs = async (page: Page, user: User) => {
  await page.addInitScript((session) => {
    localStorage.setItem("lei-do-bem:session", JSON.stringify(session));
  }, user);
};

/** Types like a person (key by key), so debounced inputs behave as in real use */
export const typeLikeAPerson = (locator: Locator, text: string) =>
  locator.pressSequentially(text, { delay: 15 });

/*
 * Benign browser noise: Chromium reports this when React Flow resizes many
 * nodes in one frame (common when tests run in parallel). Not an app error.
 */
const IGNORED_ERRORS = [/ResizeObserver loop/];

/**
 * Every test fails if the page logs an error or throws: a broken screen
 * that still "passes" the clicks is not a pass.
 */
export const test = base.extend<{ pageErrors: string[] }>({
  pageErrors: [
    async ({ page }, run) => {
      const errors: string[] = [];
      const record = (text: string) => {
        if (!IGNORED_ERRORS.some((pattern) => pattern.test(text))) errors.push(text);
      };
      page.on("pageerror", (error) => record(error.message));
      page.on("console", (message) => {
        if (message.type() === "error") record(message.text());
      });
      await run(errors);
      expect(errors, "erros no console da página").toEqual([]);
    },
    { auto: true },
  ],
});

export { expect };

/** Pill dropdown of the design (role combobox): its accessible name starts with the label */
export const combobox = (page: Page, label: string) =>
  page.getByRole("combobox", { name: new RegExp(`^${label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`) });

/** Opens the pill dropdown and picks an option, like a person would */
export const chooseOption = async (page: Page, label: string, option: string) => {
  await combobox(page, label).click();
  await page.getByRole("option", { name: option, exact: true }).click();
};
