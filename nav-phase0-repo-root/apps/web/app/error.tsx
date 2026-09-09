"use client";

export default function Error({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="max-w-prose space-y-3">
      <h1 className="text-xl font-semibold tracking-tight text-critical">
        This screen failed to render
      </h1>
      <p className="text-sm text-muted">
        The console could not build the page. Check the browser console and the API
        logs for the matching request id.
      </p>
      <button
        type="button"
        onClick={reset}
        className="rounded-panel border border-primary/50 bg-primary/10 px-3 py-1 text-xs font-medium text-primary"
      >
        Try again
      </button>
    </div>
  );
}
