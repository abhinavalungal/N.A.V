"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Panel, PanelHeader } from "@/components/ui/card";
import { Input, Labelled, Select } from "@/components/ui/controls";
import { ErrorNote, Loading } from "@/components/ui/feedback";
import { useApi } from "@/hooks/useApi";
import { api } from "@/lib/api";
import { num } from "@/lib/format";

function defaultDeparture(): string {
  const d = new Date(Date.now() + 6 * 3600 * 1000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}T${pad(
    d.getUTCHours(),
  )}:00`;
}

export default function NewVoyagePage() {
  const router = useRouter();
  const vessels = useApi(() => api.vessels());
  const ports = useApi(() => api.ports());

  const [vesselId, setVesselId] = useState<string>("");
  const [origin, setOrigin] = useState("Singapore");
  const [destination, setDestination] = useState("Rotterdam");
  const [departure, setDeparture] = useState(defaultDeparture());
  const [speed, setSpeed] = useState("13.5");
  const [cargo, setCargo] = useState("45000");
  const [required, setRequired] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!vesselId && vessels.data?.length) setVesselId(String(vessels.data[0].id));
  }, [vessels.data, vesselId]);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const voyage = await api.createVoyage({
        vessel_id: Number(vesselId),
        origin_port: origin,
        destination_port: destination,
        departure_utc: `${departure}:00`,
        planned_speed_kn: Number(speed),
        cargo_t: Number(cargo),
        required_arrival_utc: required ? `${required}:00` : null,
      });
      router.push(`/voyage?id=${voyage.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "The voyage could not be created");
      setBusy(false);
    }
  }

  const selected = vessels.data?.find((v) => String(v.id) === vesselId);

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div>
        <h1 className="text-xl font-medium">Plan a voyage</h1>
        <p className="mt-1 text-xs text-dim">
          The backend routes the leg through the sea-lane graph, samples weather along it and
          calculates the fuel and ETA before the voyage is saved.
        </p>
      </div>

      <Panel>
        <PanelHeader title="Voyage particulars" />
        {vessels.loading || ports.loading ? <Loading /> : null}
        <div className="grid gap-4 p-4 sm:grid-cols-2">
          <Labelled label="Vessel">
            <Select
              className="font-sans"
              value={vesselId}
              onChange={(e) => setVesselId(e.target.value)}
            >
              {(vessels.data ?? []).map((vessel) => (
                <option key={vessel.id} value={vessel.id}>
                  {vessel.name} — {vessel.vessel_type}
                </option>
              ))}
            </Select>
          </Labelled>

          <Labelled
            label="Cargo"
            hint={selected ? `Deadweight ${num(selected.deadweight_t)} t` : undefined}
          >
            <Input type="number" value={cargo} onChange={(e) => setCargo(e.target.value)} />
          </Labelled>

          <Labelled label="Load port">
            <Select className="font-sans" value={origin} onChange={(e) => setOrigin(e.target.value)}>
              {(ports.data ?? []).map((port) => (
                <option key={port.unlocode} value={port.name}>
                  {port.name} ({port.unlocode})
                </option>
              ))}
            </Select>
          </Labelled>

          <Labelled label="Discharge port">
            <Select
              className="font-sans"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
            >
              {(ports.data ?? []).map((port) => (
                <option key={port.unlocode} value={port.name}>
                  {port.name} ({port.unlocode})
                </option>
              ))}
            </Select>
          </Labelled>

          <Labelled label="Departure" hint="UTC">
            <Input
              type="datetime-local"
              value={departure}
              onChange={(e) => setDeparture(e.target.value)}
            />
          </Labelled>

          <Labelled label="Required arrival" hint="UTC, optional laycan">
            <Input
              type="datetime-local"
              value={required}
              onChange={(e) => setRequired(e.target.value)}
            />
          </Labelled>

          <Labelled
            label="Planned speed"
            hint={selected ? `Design speed ${num(selected.design_speed_kn, 1)} kn` : "knots"}
          >
            <Input
              type="number"
              step="0.1"
              min="4"
              max="30"
              value={speed}
              onChange={(e) => setSpeed(e.target.value)}
            />
          </Labelled>
        </div>

        {error ? <ErrorNote message={error} className="mx-4 mb-4" /> : null}

        <div className="flex items-center gap-2 border-t border-hairline p-4">
          <Button variant="primary" onClick={submit} disabled={busy || !vesselId}>
            {busy ? "Calculating route" : "Create voyage"}
          </Button>
          <Button variant="ghost" onClick={() => router.back()}>
            Cancel
          </Button>
          {origin === destination ? (
            <span className="ml-auto text-2xs text-coral">
              Load and discharge port must differ.
            </span>
          ) : null}
        </div>
      </Panel>
    </div>
  );
}
