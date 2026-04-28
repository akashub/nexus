export default function Logo({ size = 24 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none">
      <defs>
        <linearGradient id="lc" x1="25" y1="25" x2="75" y2="75" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#cbd5e1" />
          <stop offset="40%" stopColor="#f1f5f9" />
          <stop offset="60%" stopColor="#94a3b8" />
          <stop offset="100%" stopColor="#e2e8f0" />
        </linearGradient>
      </defs>
      {/* Back of loop A */}
      <ellipse cx="40" cy="50" rx="16" ry="24" transform="rotate(-30,40,50)"
        stroke="url(#lc)" strokeWidth="5" fill="none" opacity="0.3" />
      {/* Full loop B */}
      <ellipse cx="60" cy="50" rx="16" ry="24" transform="rotate(30,60,50)"
        stroke="url(#lc)" strokeWidth="5" fill="none" opacity="0.8" />
      {/* Front of loop A (crosses over B) */}
      <ellipse cx="40" cy="50" rx="16" ry="24" transform="rotate(-30,40,50)"
        stroke="url(#lc)" strokeWidth="5" fill="none" opacity="0.8"
        strokeDasharray="40 120" strokeDashoffset="-50" />
    </svg>
  );
}
