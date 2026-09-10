import { Suspense } from "react";

import { VesselDetailView } from "@/components/vessel/VesselDetailView";
import { Loading } from "@/components/ui/feedback";

export default function VesselPage() {
  return (
    <Suspense fallback={<Loading label="Loading vessel" />}>
      <VesselDetailView />
    </Suspense>
  );
}
