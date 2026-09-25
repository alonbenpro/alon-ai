import { ExperimentCreation } from "@/components/experiments/experiment-creation";
import { getExperimentRuntime } from "@/lib/operator/server";

export default async function NewExperimentPage() {
  const runtime = await getExperimentRuntime();
  return <ExperimentCreation runtime={runtime} />;
}
