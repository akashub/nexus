export default function Logo({ size = 24 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none">
      <defs>
        <linearGradient id="ln" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#60a5fa" stopOpacity="0.4" />
          <stop offset="100%" stopColor="#a78bfa" stopOpacity="0.4" />
        </linearGradient>
        <linearGradient id="ng" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#60a5fa" />
          <stop offset="100%" stopColor="#a78bfa" />
        </linearGradient>
        <radialGradient id="gl">
          <stop offset="0%" stopColor="#7dd3fc" stopOpacity="0.5" />
          <stop offset="100%" stopColor="#7dd3fc" stopOpacity="0" />
        </radialGradient>
      </defs>
      <g stroke="url(#ln)" strokeWidth="1.5" strokeLinecap="round">
        <line x1="48" y1="44" x2="25" y2="28" />
        <line x1="48" y1="44" x2="72" y2="32" />
        <line x1="48" y1="44" x2="30" y2="68" />
        <line x1="48" y1="44" x2="70" y2="65" />
        <line x1="25" y1="28" x2="72" y2="32" />
        <line x1="30" y1="68" x2="70" y2="65" />
      </g>
      <circle cx="48" cy="44" r="7" fill="url(#gl)" />
      <circle cx="25" cy="28" r="3.5" fill="#60a5fa" />
      <circle cx="72" cy="32" r="3.8" fill="#818cf8" />
      <circle cx="30" cy="68" r="3.2" fill="#60a5fa" />
      <circle cx="70" cy="65" r="3.4" fill="#a78bfa" />
      <circle cx="48" cy="44" r="5" fill="url(#ng)" />
      <circle cx="48" cy="44" r="3" fill="#e0e7ff" fillOpacity="0.25" />
    </svg>
  );
}
