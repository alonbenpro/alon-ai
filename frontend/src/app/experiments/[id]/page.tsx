import { ExperimentCreation } from "@/components/experiments/experiment-creation";
import { getExperimentRuntime } from "@/lib/operator/server";

export default async function ExperimentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const runtime = await getExperimentRuntime();
  return <ExperimentCreation experimentId={id} runtime={runtime} />;
}
