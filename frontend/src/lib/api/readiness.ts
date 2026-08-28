import { apiClient } from "@/lib/api/client";

export async function fetchReadiness() {
  const { data, error } = await apiClient.GET("/health/ready");

  if (error || !data) {
    throw new Error("API readiness check failed");
  }

  return data;
}
