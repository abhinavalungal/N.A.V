import { cn } from "@/lib/utils";

export interface Stat {
  label: string;
  value: string;
  unit?: string;
  hint?: string;
  tone?: "default" | "brass" | "kelp" | "coral";
}

const tones = {
  default: "text-ink",
  brass: "text-brass",
  kelp: "text-kelp",
  coral: "text-coral",
};

export function StatStrip({ stats }: { stats: Stat[] }) {
  return (
    <section className="grid grid-cols-2 gap-px border border-hairline bg-hairline md:grid-cols-3 xl:grid-cols-6">
      {stats.map((stat) => (
        <div key={stat.label} className="bg-hull px-4 py-3.5">
          <div className="label">{stat.label}</div>
          <div className="mt-1.5 flex items-baseline gap-1.5">
            <span
              className={cn(
                "font-mono tnum text-2xl leading-none",
                tones[stat.tone ?? "default"],
              )}
            >
              {stat.value}
            </span>
            {stat.unit ? <span className="text-xs text-faint">{stat.unit}</span> : null}
          </div>
          {stat.hint ? <div className="mt-1.5 text-2xs text-faint">{stat.hint}</div> : null}
        </div>
      ))}
    </section>
  );
}
