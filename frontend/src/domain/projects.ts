/**
 * Short code shown as "Projeto 38": the number of a generated id ("g038" → "38"),
 * otherwise the id itself in capitals ("p1" → "P1"). Also searchable.
 */
export const projectCode = (id: string) => {
  const generated = /^g0*(\d+)$/.exec(id);
  return generated ? generated[1] : id.toUpperCase();
};
