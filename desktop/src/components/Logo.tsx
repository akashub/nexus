import { useTheme } from "../hooks/useTheme";

export default function Logo({ size = 24 }: { size?: number }) {
  const { resolved } = useTheme();
  const dark = resolved === "dark";
  const id = dark ? "lc-d" : "lc-l";
  const stops = dark
    ? [["#cbd5e1", 0], ["#f1f5f9", 40], ["#94a3b8", 60], ["#e2e8f0", 100]] as const
    : [["#334155", 0], ["#1e293b", 40], ["#64748b", 60], ["#334155", 100]] as const;

  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none">
      <defs>
        <linearGradient id={id} x1="25" y1="25" x2="75" y2="75" gradientUnits="userSpaceOnUse">
          {stops.map(([c, o]) => <stop key={o} offset={`${o}%`} stopColor={c} />)}
        </linearGradient>
      </defs>
      <ellipse cx="40" cy="50" rx="16" ry="24" transform="rotate(-30,40,50)"
        stroke={`url(#${id})`} strokeWidth="5" fill="none" opacity="0.3" />
      <ellipse cx="60" cy="50" rx="16" ry="24" transform="rotate(30,60,50)"
        stroke={`url(#${id})`} strokeWidth="5" fill="none" opacity="0.8" />
      <ellipse cx="40" cy="50" rx="16" ry="24" transform="rotate(-30,40,50)"
        stroke={`url(#${id})`} strokeWidth="5" fill="none" opacity="0.8"
        strokeDasharray="40 120" strokeDashoffset="-50" />
    </svg>
  );
}
