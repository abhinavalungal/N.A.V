import { Suspense } from "react";

import { VoyageDetailView } from "@/components/voyage/VoyageDetailView";
import { Loading } from "@/components/ui/feedback";

// Static export needs a real page here; the voyage id arrives as ?id=…
// and useSearchParams has to sit inside a Suspense boundary.
export default function VoyagePage() {
  return (
    <Suspense fallback={<Loading label="Loading voyage" />}>
      <VoyageDetailView />
    </Suspense>
  );
}
