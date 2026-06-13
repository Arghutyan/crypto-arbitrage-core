interface ExchangeBadgeProps {
  name: string;
  tone?: "buy" | "sell";
}

/** Small pill identifying an exchange, tinted by trade side. */
export default function ExchangeBadge({ name, tone }: ExchangeBadgeProps) {
  const toneClass =
    tone === "buy"
      ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-300"
      : tone === "sell"
        ? "border-rose-500/25 bg-rose-500/10 text-rose-300"
        : "border-white/10 bg-base-700/60 text-slate-300";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium ${toneClass}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />
      {name}
    </span>
  );
}
