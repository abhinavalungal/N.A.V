import type { Fetched, MetaResponse } from "@nav/shared-types";

import { Badge } from "@/components/ui/badge";
import { Panel, PanelHeader } from "@/components/ui/panel";

/**
 * Providers are named with the implementation actually in use. A mocked
 * provider is labelled as mock everywhere it appears.
 */
export function ServicePanel({ meta }: { meta: Fetched<MetaResponse> }) {
  if (!meta.ok) {
    return (
      <Panel>
        <PanelHeader title="Build and providers" />
        <p className="px-4 py-6 text-sm text-muted">{meta.reason}.</p>
      </Panel>
    );
  }

  const { data } = meta;
  const providers = [
    { label: "Language model", value: data.llm_provider, key: "llm" },
    { label: "Weather", value: data.weather_provider, key: "weather" },
    { label: "Routing", value: data.routing_provider, key: "routing" },
  ];

  return (
    <Panel>
      <PanelHeader title="Build and providers" description={data.phase} />
      <dl className="divide-y">
        <div className="flex items-baseline justify-between px-4 py-2.5">
          <dt className="text-sm text-muted">Version</dt>
          <dd className="tabular font-mono text-sm">{data.version}</dd>
        </div>
        <div className="flex items-baseline justify-between px-4 py-2.5">
          <dt className="text-sm text-muted">Environment</dt>
          <dd className="font-mono text-sm">{data.environment}</dd>
        </div>
        <div className="flex items-baseline justify-between px-4 py-2.5">
          <dt className="text-sm text-muted">API</dt>
          <dd className="font-mono text-sm">{data.api_version}</dd>
        </div>
        {providers.map((provider) => (
          <div
            key={provider.key}
            className="flex items-center justify-between gap-3 px-4 py-2.5"
          >
            <dt className="text-sm text-muted">{provider.label}</dt>
            <dd className="flex items-center gap-2">
              <span className="font-mono text-sm">{provider.value}</span>
              {data.mock_providers.includes(provider.key) ? (
                <Badge tone="signal">mock data</Badge>
              ) : null}
            </dd>
          </div>
        ))}
      </dl>
    </Panel>
  );
}
