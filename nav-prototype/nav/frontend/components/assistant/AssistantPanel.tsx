"use client";

import { Check, CircleDashed, Send, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { AgentStep } from "@/types";

interface Turn {
  role: "user" | "assistant";
  content: string;
  steps?: AgentStep[];
  provider?: string;
  ms?: number;
  failed?: boolean;
}

const PLAN = [
  "Reading voyage and vessel data",
  "Retrieving weather",
  "Running calculations",
  "Preparing the answer",
];

export function AssistantPanel({
  voyageId,
  suggestions,
  className,
  onRunComplete,
  intro,
}: {
  voyageId?: number | null;
  suggestions?: string[];
  className?: string;
  onRunComplete?: (runId: number) => void;
  intro?: string;
}) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [planStep, setPlanStep] = useState(0);
  const scroller = useRef<HTMLDivElement | null>(null);
  const sessionId = useRef(`ui-${Math.random().toString(36).slice(2, 8)}`);

  const prompts = suggestions ?? [
    "Optimize this voyage for minimum fuel",
    "Why did you choose this route?",
    "What happens if I increase speed to 14 knots?",
    "Compare this voyage with the last five voyages",
  ];

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [turns, busy, planStep]);

  useEffect(() => {
    if (!busy) return;
    setPlanStep(0);
    const timer = setInterval(() => setPlanStep((s) => Math.min(s + 1, PLAN.length - 1)), 700);
    return () => clearInterval(timer);
  }, [busy]);

  async function send(message: string) {
    if (!message.trim() || busy) return;
    setInput("");
    setTurns((t) => [...t, { role: "user", content: message }]);
    setBusy(true);
    try {
      const response = await api.chat({
        message,
        session_id: sessionId.current,
        voyage_id: voyageId ?? null,
      });
      setTurns((t) => [
        ...t,
        {
          role: "assistant",
          content: response.answer,
          steps: response.steps,
          provider: response.provider,
          ms: response.duration_ms,
        },
      ]);
      if (response.data?.run_id && onRunComplete) onRunComplete(Number(response.data.run_id));
    } catch (error) {
      setTurns((t) => [
        ...t,
        {
          role: "assistant",
          content: error instanceof Error ? error.message : "The assistant is unavailable.",
          failed: true,
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className={cn("panel flex min-h-0 flex-col", className)}>
      <header className="panel-header">
        <div>
          <h2 className="text-sm font-medium">N.A.V. Assistant</h2>
          <p className="mt-0.5 text-xs text-faint">
            Answers from backend tools, never from guesswork
          </p>
        </div>
        {turns.length > 0 ? (
          <Button variant="ghost" size="sm" onClick={() => setTurns([])} aria-label="Clear chat">
            <X className="h-3.5 w-3.5" />
          </Button>
        ) : null}
      </header>

      <div ref={scroller} className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {turns.length === 0 ? (
          <p className="text-xs leading-relaxed text-dim">
            {intro ??
              "Ask about a voyage and N.A.V. calls the routing, weather, fuel, ETA, emissions and optimization tools, then explains what they returned."}
          </p>
        ) : null}

        {turns.map((turn, i) =>
          turn.role === "user" ? (
            <div key={i} className="flex justify-end">
              <p className="max-w-[85%] border border-hairline bg-deck px-3 py-2 text-xs text-ink">
                {turn.content}
              </p>
            </div>
          ) : (
            <div key={i} className="space-y-2">
              {turn.steps && turn.steps.length > 0 ? (
                <ul className="space-y-1 border-l border-hairline pl-3">
                  {turn.steps.map((step, n) => (
                    <li
                      key={n}
                      className={cn(
                        "flex items-center gap-2 text-2xs",
                        step.status === "failed" ? "text-coral" : "text-faint",
                      )}
                    >
                      {step.status === "failed" ? (
                        <X className="h-3 w-3" />
                      ) : (
                        <Check className="h-3 w-3 text-kelp" />
                      )}
                      {step.label}
                      {step.detail ? <span className="text-coral">— {step.detail}</span> : null}
                    </li>
                  ))}
                </ul>
              ) : null}
              <p
                className={cn(
                  "whitespace-pre-wrap text-xs leading-relaxed",
                  turn.failed ? "text-coral" : "text-ink",
                )}
              >
                {turn.content}
              </p>
              {turn.provider ? (
                <p className="text-2xs text-faint">
                  {turn.provider === "mock" ? "Mock agent" : `OpenAI · ${turn.provider}`} ·{" "}
                  {turn.ms} ms
                </p>
              ) : null}
            </div>
          ),
        )}

        {busy ? (
          <ul className="space-y-1 border-l border-brass/40 pl-3">
            {PLAN.map((label, i) => (
              <li
                key={label}
                className={cn(
                  "flex items-center gap-2 text-2xs",
                  i <= planStep ? "text-dim" : "text-faint/50",
                )}
              >
                <CircleDashed
                  className={cn("h-3 w-3", i === planStep && "animate-spin text-brass")}
                />
                {label}
              </li>
            ))}
          </ul>
        ) : null}
      </div>

      <div className="border-t border-hairline p-3">
        {turns.length === 0 ? (
          <div className="mb-3 flex flex-wrap gap-1.5">
            {prompts.map((prompt) => (
              <button
                key={prompt}
                onClick={() => send(prompt)}
                className="border border-hairline bg-deck px-2 py-1 text-2xs text-dim transition-colors hover:border-[#2c4459] hover:text-ink"
              >
                {prompt}
              </button>
            ))}
          </div>
        ) : null}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
          className="flex gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask N.A.V."
            disabled={busy}
            className="h-9 flex-1 rounded-sm border border-hairline bg-deck px-2.5 text-xs text-ink placeholder:text-faint focus:border-[#33506a]"
          />
          <Button type="submit" variant="primary" size="md" disabled={busy || !input.trim()}>
            <Send className="h-3.5 w-3.5" />
          </Button>
        </form>
      </div>
    </section>
  );
}
