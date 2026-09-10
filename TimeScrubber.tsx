"use client";

import { Pause, Play } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { cn } from "@/lib/utils";

const DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const STEP_HOURS = 6;

function parse(value: string): number {
  return new Date(value.endsWith("Z") ? value : `${value}Z`).getTime();
}

/**
 * Steps the chart through the passage in six-hour jumps, the way a router's
 * timeline does. Emits the selected moment; the page decides what to reload.
 */
export function TimeScrubber({
  from,
  to,
  value,
  onChange,
  className,
}: {
  from: string;
  to: string;
  value: Date;
  onChange: (moment: Date) => void;
  className?: string;
}) {
  const [playing, setPlaying] = useState(false);

  const steps = useMemo(() => {
    const start = parse(from);
    const end = parse(to);
    const count = Math.max(1, Math.round((end - start) / (STEP_HOURS * 3600 * 1000)));
    // Keep the strip readable on very long passages.
    const stride = Math.max(1, Math.ceil(count / 60));
    const out: Date[] = [];
    for (let i = 0; i <= count; i += stride) {
      out.push(new Date(start + i * STEP_HOURS * 3600 * 1000));
    }
    if (out[out.length - 1].getTime() < end) out.push(new Date(end));
    return out;
  }, [from, to]);

  const index = useMemo(() => {
    let best = 0;
    let bestDelta = Infinity;
    steps.forEach((step, i) => {
      const delta = Math.abs(step.getTime() - value.getTime());
      if (delta < bestDelta) {
        bestDelta = delta;
        best = i;
      }
    });
    return best;
  }, [steps, value]);

  useEffect(() => {
    if (!playing) return;
    const timer = setInterval(() => {
      const next = index + 1;
      if (next >= steps.length) {
        setPlaying(false);
        return;
      }
      onChange(steps[next]);
    }, 900);
    return () => clearInterval(timer);
  }, [playing, index, steps, onChange]);

  // A tick per day, so the strip reads as dates rather than as numbers.
  const dayTicks = useMemo(() => {
    const seen = new Set<string>();
    return steps.map((step, i) => {
      const key = step.toISOString().slice(0, 10);
      if (seen.has(key)) return { i, label: null };
      seen.add(key);
      return {
        i,
        label: `${DAY_LABELS[step.getUTCDay()]} ${step.getUTCDate()}`,
      };
    });
  }, [steps]);

  const current = steps[index] ?? new Date(parse(from));

  return (
    <div className={cn("flex items-center gap-3 border-t border-hairline px-3 py-2", className)}>
      <button
        onClick={() => setPlaying((p) => !p)}
        aria-label={playing ? "Pause" : "Play through the passage"}
        className="flex h-7 w-7 shrink-0 items-center justify-center border border-hairline bg-deck text-dim hover:text-ink"
      >
        {playing ? <Pause className="h-3 w-3" /> : <Play className="h-3 w-3" />}
      </button>

      <div className="min-w-0 flex-1">
        <input
          type="range"
          min={0}
          max={steps.length - 1}
          value={index}
          onChange={(e) => onChange(steps[Number(e.target.value)])}
          className="h-1 w-full cursor-pointer appearance-none rounded-sm bg-deck accent-brass"
          aria-label="Time along the passage"
        />
        <div className="mt-1 flex justify-between text-2xs text-faint">
          {dayTicks
            .filter((t) => t.label)
            .filter((_, n, all) => all.length <= 8 || n % Math.ceil(all.length / 8) === 0)
            .map((t) => (
              <span key={t.i} className="font-mono">
                {t.label}
              </span>
            ))}
        </div>
      </div>

      <div className="shrink-0 text-right">
        <div className="font-mono tnum text-xs text-ink">
          {`${DAY_LABELS[current.getUTCDay()]} ${current.getUTCDate()} ${String(
            current.getUTCHours(),
          ).padStart(2, "0")}:00`}
        </div>
        <div className="text-2xs text-faint">UTC</div>
      </div>
    </div>
  );
}
