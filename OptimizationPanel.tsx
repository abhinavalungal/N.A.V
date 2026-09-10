"use client";

import { Check, ChevronRight, CircleDashed, Play, X } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge, RiskBadge, StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field, Panel, PanelHeader } from "@/components/ui/card";
import { Input, Labelled, Select } from "@/components/ui/controls";
import { ErrorNote } from "@/components/ui/feedback";
import { api } from "@/lib/api";
import { conditionWords } from "@/components/voyage/LegSchedule";
import { OBJECTIVE_LABELS, hours, num, utcShort } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { OptimizationOption, OptimizationRun, Recommendation, Voyage } from "@/types";

const STAGES = [
  "Analyzing voyage",
  "Evaluating routes",
  "Calculating fuel",
  "Comparing options",
  "Generating recommendation",
];

export function OptimizationPanel({
  voyage,
  initialRun,
  onRun,
  onSelectOption,
  selectedOptionId,
}: {
  voyage: Voyage;
  initialRun?: OptimizationRun | null;
  onRun?: (run: OptimizationRun) => void;
  onSelectOption?: (option: OptimizationOption | null) => void;
  selectedOptionId?: number | null;
}) {
  const [objective, setObjective] = useState("BALANCED");
  const [maxSpeed, setMaxSpeed] = useState("");
  const [minSpeed, setMinSpeed] = useState("");
  const [arrival, setArrival] = useState("");
  const [maxRisk, setMaxRisk] = useState("");
  const [run, setRun] = useState<OptimizationRun | null>(initialRun ?? null);
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialRun) setRun(initialRun);
  }, [initialRun]);

  useEffect(() => {
    if (!busy) return;
    setStage(0);
    const timer = setInterval(() => setStage((s) => Math.min(s + 1, STAGES.length - 1)), 550);
    return () => clearInterval(timer);
  }, [busy]);

  async function optimize() {
    setBusy(true);
    setError(null);
    try {
      const result = await api.optimize({
        voyage_id: voyage.id,
        objective,
        constraints: {
          max_speed_kn: maxSpeed ? Number(maxSpeed) : null,
          min_speed_kn: minSpeed ? Number(minSpeed) : null,
          required_arrival_utc: arrival ? `${arrival}:00` : null,
          max_weather_risk: maxRisk || null,
        },
      });
      setRun(result);
      onRun?.(result);
      onSelectOption?.(result.options.find((o) => o.recommended) ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Optimization failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <Panel>
        <PanelHeader
          title="Voyage optimization"
          caption={`${voyage.origin_port} to ${voyage.destination_port} · ${num(
            voyage.distance_remaining_nm,
          )} NM remaining`}
          actions={
            <Button variant="primary" size="md" onClick={optimize} disabled={busy}>
              {busy ? (
                <CircleDashed className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Play className="h-3.5 w-3.5" />
              )}
              Run N.A.V. optimization
            </Button>
          }
        />
        <div className="grid gap-4 p-4 md:grid-cols-2 xl:grid-cols-5">
          <Labelled label="Objective">
            <Select value={objective} onChange={(e) => setObjective(e.target.value)}>
              {Object.entries(OBJECTIVE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
          </Labelled>
          <Labelled label="Maximum speed" hint="knots">
            <Input
              type="number"
              step="0.1"
              min="1"
              max="40"
              placeholder="no limit"
              value={maxSpeed}
              onChange={(e) => setMaxSpeed(e.target.value)}
            />
          </Labelled>
          <Labelled label="Minimum speed" hint="knots">
            <Input
              type="number"
              step="0.1"
              min="1"
              max="40"
              placeholder="no limit"
              value={minSpeed}
              onChange={(e) => setMinSpeed(e.target.value)}
            />
          </Labelled>
          <Labelled label="Required arrival" hint="UTC">
            <Input
              type="datetime-local"
              value={arrival}
              onChange={(e) => setArrival(e.target.value)}
            />
          </Labelled>
          <Labelled label="Maximum weather risk">
            <Select value={maxRisk} onChange={(e) => setMaxRisk(e.target.value)}>
              <option value="">Any</option>
              <option value="VERY_LOW">Very low</option>
              <option value="LOW">Low</option>
              <option value="MODERATE">Moderate</option>
              <option value="HIGH">High</option>
            </Select>
          </Labelled>
        </div>

        {busy ? (
          <ul className="space-y-1.5 border-t border-hairline px-4 py-4">
            {STAGES.map((label, i) => (
              <li
                key={label}
                className={cn(
                  "flex items-center gap-2 text-xs",
                  i < stage ? "text-dim" : i === stage ? "text-ink" : "text-faint/50",
                )}
              >
                {i < stage ? (
                  <Check className="h-3.5 w-3.5 text-kelp" />
                ) : (
                  <CircleDashed
                    className={cn("h-3.5 w-3.5", i === stage && "animate-spin text-brass")}
                  />
                )}
                {label}
              </li>
            ))}
          </ul>
        ) : null}

        {error ? <ErrorNote message={error} className="m-4" /> : null}
      </Panel>

      {run && !busy ? (
        <RunResult
          run={run}
          onSelectOption={onSelectOption}
          selectedOptionId={selectedOptionId}
          onRecommendation={(rec) =>
            setRun({ ...run, recommendation: rec, recommended_option_id: rec.option_id })
          }
        />
      ) : null}
    </div>
  );
}

function RunResult({
  run,
  onSelectOption,
  selectedOptionId,
  onRecommendation,
}: {
  run: OptimizationRun;
  onSelectOption?: (option: OptimizationOption | null) => void;
  selectedOptionId?: number | null;
  onRecommendation: (rec: Recommendation) => void;
}) {
  if (run.status !== "COMPLETED") {
    return (
      <Panel>
        <PanelHeader title="No feasible option found" />
        <div className="space-y-3 p-4">
          <p className="text-xs text-dim">{run.message}</p>
          <ul className="space-y-1.5">
            {run.options.map((option) => (
              <li key={option.id} className="flex items-start gap-2 text-xs text-faint">
                <X className="mt-0.5 h-3.5 w-3.5 shrink-0 text-coral" />
                <span>
                  <span className="text-dim">{option.label}</span> — {option.infeasible_reason}
                </span>
              </li>
            ))}
          </ul>
          <p className="text-2xs text-faint">
            N.A.V. does not invent a compromise. Relax a constraint and run it again.
          </p>
        </div>
      </Panel>
    );
  }

  return (
    <div className="space-y-4">
      {run.recommendation ? (
        <RecommendationBlock
          run={run}
          recommendation={run.recommendation}
          onRecommendation={onRecommendation}
        />
      ) : null}
      <OptionsComparison
        run={run}
        onSelectOption={onSelectOption}
        selectedOptionId={selectedOptionId}
      />
      <ActivityTrace run={run} />
    </div>
  );
}

export function RecommendationBlock({
  run,
  recommendation,
  onRecommendation,
}: {
  run: OptimizationRun;
  recommendation: Recommendation;
  onRecommendation: (rec: Recommendation) => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [modifying, setModifying] = useState(false);
  const [choice, setChoice] = useState<number>(recommendation.option_id);
  const option = run.options.find((o) => o.id === recommendation.option_id);

  async function decide(kind: "approve" | "reject" | "modify") {
    setBusy(kind);
    setError(null);
    try {
      const updated =
        kind === "approve"
          ? await api.approve(recommendation.id)
          : kind === "reject"
            ? await api.reject(recommendation.id)
            : await api.modify(recommendation.id, choice);
      onRecommendation(updated);
      setModifying(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "That decision could not be recorded");
    } finally {
      setBusy(null);
    }
  }

  const decided = recommendation.status !== "PENDING";

  return (
    <Panel className={cn(!decided && "border-l-2 border-l-brass")}>
      <PanelHeader
        title="N.A.V. recommendation"
        caption={`${recommendation.vessel_name ?? ""} · ${recommendation.voyage_reference ?? ""}`}
        actions={<StatusBadge status={recommendation.status} />}
      />
      <div className="grid gap-4 border-b border-hairline p-4 sm:grid-cols-3 xl:grid-cols-6">
        <Field label="Recommended" value={option?.label ?? recommendation.route_label ?? "—"} mono={false} />
        <Field label="Fuel" value={`${num(option?.fuel_mt, 1)} MT`} />
        <Field
          label="Fuel saving"
          value={
            <span className={recommendation.fuel_saving_mt > 0 ? "text-kelp" : undefined}>
              {num(recommendation.fuel_saving_mt, 1)} MT
              {typeof option?.breakdown_json?.bunker_price_usd_per_mt === "number" ? (
                <span className="ml-1.5 text-2xs text-faint">
                  ≈ $
                  {num(
                    recommendation.fuel_saving_mt *
                      (option.breakdown_json.bunker_price_usd_per_mt as number),
                  )}
                </span>
              ) : null}
            </span>
          }
        />
        <Field label="ETA" value={`${utcShort(option?.eta_utc)} UTC`} />
        <Field label="CO2" value={`${num(option?.co2_mt, 1)} MT`} />
        <Field
          label="Weather risk"
          value={option ? <RiskBadge band={option.weather_risk} /> : "—"}
          mono={false}
        />
      </div>

      <div className="border-b border-hairline p-4">
        <h3 className="text-xs font-medium text-dim">Why N.A.V. recommends this</h3>
        <p className="mt-2 max-w-[68ch] text-sm leading-relaxed text-ink">
          {recommendation.rationale}
        </p>
        <p className="mt-2 text-2xs text-faint">
          Objective {OBJECTIVE_LABELS[run.objective]} · weather source{" "}
          {run.weather_source === "OPEN_METEO" ? "Open-Meteo" : "mock provider"} ·{" "}
          {recommendation.eta_delta_hours >= 0 ? "arrives " : "arrives "}
          {hours(Math.abs(recommendation.eta_delta_hours))}{" "}
          {recommendation.eta_delta_hours >= 0 ? "later" : "earlier"} than the fastest option
        </p>
      </div>

      {error ? <ErrorNote message={error} className="m-4" /> : null}

      {decided ? (
        <div className="flex items-center gap-2 p-4 text-xs text-kelp">
          <Check className="h-4 w-4" />
          Recommendation {recommendation.status.toLowerCase()}. The voyage plan now uses{" "}
          {option?.label} at {num(option?.average_speed_kn, 1)} kn.
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-2 p-4">
          <Button variant="approve" onClick={() => decide("approve")} disabled={busy !== null}>
            <Check className="h-3.5 w-3.5" />
            Approve
          </Button>
          <Button variant="danger" onClick={() => decide("reject")} disabled={busy !== null}>
            <X className="h-3.5 w-3.5" />
            Reject
          </Button>
          {modifying ? (
            <div className="flex flex-wrap items-center gap-2">
              <Select
                className="h-9 w-56"
                value={choice}
                onChange={(e) => setChoice(Number(e.target.value))}
              >
                {run.options
                  .filter((o) => o.feasible)
                  .map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.label} — {num(o.fuel_mt, 1)} MT, ETA {utcShort(o.eta_utc)}
                    </option>
                  ))}
              </Select>
              <Button variant="primary" onClick={() => decide("modify")} disabled={busy !== null}>
                Save choice
              </Button>
              <Button variant="ghost" onClick={() => setModifying(false)}>
                Cancel
              </Button>
            </div>
          ) : (
            <Button variant="secondary" onClick={() => setModifying(true)} disabled={busy !== null}>
              Modify
            </Button>
          )}
          <span className="ml-auto text-2xs text-faint">
            Approval updates the voyage plan only. N.A.V. never controls the vessel.
          </span>
        </div>
      )}
    </Panel>
  );
}

export function OptionsComparison({
  run,
  onSelectOption,
  selectedOptionId,
}: {
  run: OptimizationRun;
  onSelectOption?: (option: OptimizationOption | null) => void;
  selectedOptionId?: number | null;
}) {
  const feasible = run.options.filter((o) => o.feasible);
  const bestFuel = Math.min(...feasible.map((o) => o.fuel_mt));
  const bestEta = Math.min(...feasible.map((o) => o.duration_hours));
  const fastest = feasible.reduce(
    (acc, o) => (acc === null || o.duration_hours < acc.duration_hours ? o : acc),
    null as OptimizationOption | null,
  );
  const costOf = (option: OptimizationOption): number | null =>
    typeof option.breakdown_json?.cost_usd === "number"
      ? (option.breakdown_json.cost_usd as number)
      : null;

  return (
    <Panel>
      <PanelHeader
        title="Options evaluated"
        caption="Lower score wins. Weights come from the selected objective."
      />
      <div className="grid gap-px bg-hairline md:grid-cols-2 xl:grid-cols-4">
        {run.options.map((option) => (
          <button
            key={option.id}
            onClick={() => onSelectOption?.(option)}
            className={cn(
              "group bg-hull p-4 text-left transition-colors hover:bg-deck",
              !option.feasible && "opacity-55",
              selectedOptionId === option.id && "bg-deck",
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm text-ink">{option.label}</span>
              {option.recommended ? <Badge tone="brass">Recommended</Badge> : null}
              {!option.feasible ? <Badge tone="alert">Excluded</Badge> : null}
            </div>
            {(() => {
              const words = conditionWords(option.risk_index);
              const cost = costOf(option);
              const reference = fastest ? costOf(fastest) : null;
              const delta = cost !== null && reference !== null ? cost - reference : null;
              return (
                <div className="mt-2 flex items-baseline justify-between gap-2">
                  <span className={cn("text-xs", words.tone)}>{words.label} conditions</span>
                  {cost !== null ? (
                    <span className="text-right">
                      <span className="font-mono tnum text-sm text-ink">
                        ${num(cost)}
                      </span>
                      {delta !== null && Math.abs(delta) > 1 ? (
                        <span
                          className={cn(
                            "ml-1.5 font-mono tnum text-2xs",
                            delta < 0 ? "text-kelp" : "text-faint",
                          )}
                        >
                          {delta < 0 ? "-" : "+"}${num(Math.abs(delta))}
                        </span>
                      ) : null}
                    </span>
                  ) : null}
                </div>
              );
            })()}
            <dl className="mt-3 space-y-1.5">
              <Row
                label="Fuel"
                value={`${num(option.fuel_mt, 1)} MT`}
                highlight={option.feasible && option.fuel_mt === bestFuel}
              />
              <Row label="ETA" value={`${utcShort(option.eta_utc)} UTC`} />
              <Row
                label="Duration"
                value={hours(option.duration_hours)}
                highlight={option.feasible && option.duration_hours === bestEta}
              />
              <Row label="CO2" value={`${num(option.co2_mt, 1)} MT`} />
              <Row label="Speed" value={`${num(option.average_speed_kn, 1)} kn`} />
              <Row label="Distance" value={`${num(option.distance_nm)} NM`} />
              <div className="flex items-center justify-between pt-1">
                <span className="label">Risk</span>
                <RiskBadge band={option.weather_risk} />
              </div>
              <Row
                label="Score"
                value={option.score === null ? "—" : option.score.toFixed(3)}
                highlight={option.recommended}
              />
            </dl>
            {option.infeasible_reason ? (
              <p className="mt-3 text-2xs text-coral">{option.infeasible_reason}</p>
            ) : (
              <p className="mt-3 flex items-center gap-1 text-2xs text-faint opacity-0 transition-opacity group-hover:opacity-100">
                Show on chart <ChevronRight className="h-3 w-3" />
              </p>
            )}
          </button>
        ))}
      </div>
    </Panel>
  );
}

function Row({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="label">{label}</span>
      <span className={cn("font-mono tnum text-xs", highlight ? "text-brass" : "text-ink")}>
        {value}
      </span>
    </div>
  );
}

export function ActivityTrace({ run }: { run: OptimizationRun }) {
  return (
    <Panel>
      <PanelHeader title="Agent activity" caption={`Run #${run.id}`} />
      <ul className="space-y-1.5 p-4">
        {run.activity.map((step, i) => (
          <li
            key={i}
            className={cn(
              "flex items-center gap-2 text-xs",
              step.status === "failed" ? "text-coral" : "text-dim",
            )}
          >
            {step.status === "failed" ? (
              <X className="h-3.5 w-3.5" />
            ) : (
              <Check className="h-3.5 w-3.5 text-kelp" />
            )}
            {step.label}
          </li>
        ))}
      </ul>
    </Panel>
  );
}
