/**
 * Lightweight pure-JS confetti — no external library needed.
 * Creates coloured <div> particles that fall and fade out, then self-clean.
 */

const COLORS = [
  '#6366F1', '#8B5CF6', '#22C55E', '#F59E0B',
  '#06B6D4', '#EF4444', '#EC4899', '#FBBF24',
];

function rnd(min: number, max: number) {
  return Math.random() * (max - min) + min;
}

export function fireConfetti(count = 120) {
  const container = document.createElement('div');
  container.style.cssText = `
    position: fixed; inset: 0; pointer-events: none; z-index: 9999; overflow: hidden;
  `;
  document.body.appendChild(container);

  for (let i = 0; i < count; i++) {
    const el = document.createElement('div');
    const color = COLORS[Math.floor(Math.random() * COLORS.length)];
    const size = rnd(6, 13);
    const startX = rnd(10, 90); // vw %
    const delay = rnd(0, 600);
    const duration = rnd(1400, 2600);
    const rotateEnd = rnd(-720, 720);
    const xDrift = rnd(-120, 120); // px

    el.style.cssText = `
      position: absolute;
      top: -20px;
      left: ${startX}vw;
      width: ${size}px;
      height: ${size * rnd(0.4, 1)}px;
      background: ${color};
      border-radius: ${Math.random() > 0.5 ? '50%' : '2px'};
      opacity: 1;
      animation: confetti-fall ${duration}ms ${delay}ms ease-in forwards;
      --x-drift: ${xDrift}px;
      --rotate-end: ${rotateEnd}deg;
    `;
    container.appendChild(el);
  }

  // Inject keyframes once
  if (!document.getElementById('confetti-style')) {
    const style = document.createElement('style');
    style.id = 'confetti-style';
    style.textContent = `
      @keyframes confetti-fall {
        0%   { transform: translate(0, 0) rotate(0deg); opacity: 1; }
        80%  { opacity: 1; }
        100% { transform: translate(var(--x-drift), 110vh) rotate(var(--rotate-end)); opacity: 0; }
      }
    `;
    document.head.appendChild(style);
  }

  // Clean up after all particles finish (max duration + delay)
  setTimeout(() => container.remove(), 3500);
}
