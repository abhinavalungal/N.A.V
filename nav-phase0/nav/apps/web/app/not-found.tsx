import Link from "next/link";

export default function NotFound() {
  return (
    <div className="max-w-prose space-y-3">
      <h1 className="text-xl font-semibold tracking-tight">No such screen</h1>
      <p className="text-sm text-muted">
        Most of N.A.V. is not built yet. The left rail marks each destination with the
        phase that will build it.
      </p>
      <Link href="/" className="inline-block text-sm text-primary underline">
        Back to system status
      </Link>
    </div>
  );
}
