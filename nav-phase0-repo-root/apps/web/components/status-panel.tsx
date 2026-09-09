import type { ComponentStatus, Fetched, ReadinessResponse } from "@nav/shared-types";

import { Badge } from "@/components/ui/badge";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { formatLatency } from "@/lib/utils";

const TONE: Record<ComponentStatus, "positive" | "critical" | "neutral"> = {
  UP: "positive",
  DOWN: "critical",
  NOT_CONFIGURED: "neutral",
  UNKNOWN: "neutral",
};

export function StatusPanel({
  readiness,
  apiUrl,
}: {
  readiness: Fetched<ReadinessResponse>;
  apiUrl: string;
}) {
  if (!readiness.ok) {
    return (
      <Panel>
        <PanelHeader
          title="Stack status"
          description={`Probing ${apiUrl}. Start the API to see dependency status.`}
        />
        <div className="px-4 py-6">
          <p className="font-mono text-2xl text-critical">API UNREACHABLE</p>
          <p className="mt-2 max-w-prose text-sm text-muted">
            {readiness.reason}. Nothing below can be reported until the API answers -
            this console shows measured status only.
          </p>
          <p className="mt-3 font-mono text-xs text-muted">docker compose up --build</p>
        </div>
      </Panel>
    );
  }

  const report = readiness.data;

  return (
    <Panel>
      <PanelHeader
        title="Stack status"
        description="Each dependency is probed on request. A component is reported UP only when it answered."
        action={
          <Badge tone={report.ready ? "positive" : "critical"}>
            {report.ready ? "Ready to serve" : "Not ready"}
          </Badge>
        }
      />

      <div className="px-4 py-5">
        <p
          className={`font-mono text-3xl tracking-tight ${
            report.ready ? "text-positive" : "text-critical"
          }`}
        >
          {report.ready ? "READY TO SERVE" : "DEPENDENCY DOWN"}
        </p>
        <p className="mt-1 tabular font-mono text-xs text-muted">
          {report.service} {report.version} · {report.environment} ·{" "}
          {new Date(report.timestamp).toISOString()}
        </p>
      </div>

      <table className="w-full text-sm">
        <caption className="sr-only">Dependency probe results</caption>
        <thead>
          <tr className="border-y text-left text-micro text-muted">
            <th scope="col" className="px-4 py-2 font-medium">
              Component
            </th>
            <th scope="col" className="px-4 py-2 font-medium">
              Status
            </th>
            <th scope="col" className="px-4 py-2 text-right font-medium">
              Probe latency
            </th>
            <th scope="col" className="px-4 py-2 font-medium">
              Detail
            </th>
          </tr>
        </thead>
        <tbody>
          {report.components.map((component) => (
            <tr key={component.name} className="border-b last:border-b-0">
              <th scope="row" className="px-4 py-2.5 text-left font-normal">
                {component.name}
              </th>
              <td className="px-4 py-2.5">
                <Badge tone={TONE[component.status]}>{component.status}</Badge>
              </td>
              <td className="tabular px-4 py-2.5 text-right font-mono text-xs">
                {formatLatency(component.latency_ms)}
              </td>
              <td className="px-4 py-2.5 font-mono text-xs text-muted">
                {component.detail ?? "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  );
}
