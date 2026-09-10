import { Badge } from "@/components/ui/badge";
import { Panel, PanelHeader } from "@/components/ui/panel";

/**
 * The build plan is a sequence, so it is numbered. Only Phase 0 is marked
 * done, and it is marked done because the checks in the repository pass.
 */
const PHASES: { id: number; title: string; state: "done" | "next" | "planned" }[] = [
  { id: 0, title: "Architecture, Docker, health, CI", state: "done" },
  { id: 1, title: "Auth, users, companies, RBAC", state: "next" },
  { id: 2, title: "Vessels, positions, voyages", state: "planned" },
  { id: 3, title: "Weather, routing, fuel, ETA, emissions", state: "planned" },
  { id: 4, title: "Optimisation engine", state: "planned" },
  { id: 5, title: "N.A.V. agent, tools, LLM provider", state: "planned" },
  { id: 6, title: "Recommendations, approval, audit", state: "planned" },
  { id: 7, title: "Dashboard, maps, agent activity", state: "planned" },
];

const TONE = { done: "positive", next: "primary", planned: "neutral" } as const;
const LABEL = { done: "built", next: "next", planned: "planned" } as const;

export function PhaseProgress() {
  return (
    <Panel>
      <PanelHeader
        title="Build sequence"
        description="Phases 8 to 12 (outcomes, RAG, AWS, monitoring, further agents) follow the same order as the specification."
      />
      <ol className="divide-y">
        {PHASES.map((phase) => (
          <li key={phase.id} className="flex items-center gap-3 px-4 py-2.5">
            <span className="tabular w-6 font-mono text-xs text-muted">
              {String(phase.id).padStart(2, "0")}
            </span>
            <span className="flex-1 text-sm">{phase.title}</span>
            <Badge tone={TONE[phase.state]}>{LABEL[phase.state]}</Badge>
          </li>
        ))}
      </ol>
    </Panel>
  );
}
