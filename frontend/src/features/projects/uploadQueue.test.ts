import { describe, expect, it } from "vitest";
import { addFiles, advance, foldRows, queueSummary } from "@/features/projects/uploadQueue";

const file = (name: string, size = 100_000) => new File([new Uint8Array(size)], name, { lastModified: 1 });

describe("upload queue", () => {
  it("adds files once and recognizes their type", () => {
    const a = file("dossie_projeto.pdf");
    const items = addFiles(addFiles([], [a]), [a, file("medicoes.csv")]);
    expect(items.map((i) => i.kind)).toEqual(["Dossiê", "Medições"]);
  });

  it("finishes the simulated upload after a few ticks", () => {
    let items = addFiles([], [file("a.pdf", 3_000_000)]);
    expect(queueSummary(items).uploading).toBe(1);
    for (let i = 0; i < 15; i++) items = advance(items);
    expect(queueSummary(items)).toMatchObject({ count: 1, uploading: 0, bytes: 3_000_000 });
  });

  it("folds the rows after the first four", () => {
    const items = addFiles([], ["a.pdf", "b.pdf", "c.pdf", "d.pdf", "metodo.md", "config.json"].map((n) => file(n)));
    const { visible, rest } = foldRows(items);
    expect(visible).toHaveLength(4);
    expect(rest).toMatchObject({ count: 2, kinds: ["método", "configuração"] });
  });

  it("does not fold a single extra row", () => {
    const items = addFiles([], ["a.pdf", "b.pdf", "c.pdf", "d.pdf", "e.pdf"].map((n) => file(n)));
    expect(foldRows(items)).toMatchObject({ rest: null });
  });
});
