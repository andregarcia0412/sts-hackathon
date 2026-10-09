/** Corner radius of the connectors in the design */
const RADIUS = 8;

/**
 * Connector of the design: horizontal out of the parent, a rounded corner, a
 * vertical run halfway between the cards, another corner, horizontal into the
 * child. Small height differences shrink the corners instead of making an S.
 */
export const bracketPath = (sx: number, sy: number, tx: number, ty: number): string => {
  const dy = ty - sy;
  if (Math.abs(dy) < 1) return `M ${sx} ${sy} H ${tx}`;
  const midX = sx + (tx - sx) / 2;
  const r = Math.min(RADIUS, Math.abs(dy) / 2, Math.abs(tx - sx) / 2);
  const dir = Math.sign(dy);
  return [
    `M ${sx} ${sy}`,
    `H ${midX - r}`,
    `Q ${midX} ${sy} ${midX} ${sy + dir * r}`,
    `V ${ty - dir * r}`,
    `Q ${midX} ${ty} ${midX + r} ${ty}`,
    `H ${tx}`,
  ].join(" ");
};
