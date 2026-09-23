import { useQuery } from "@tanstack/react-query";

import { apiRequest, type ApiError } from "@/shared/api";

type HealthDto = { status: "ok"; service: string };

export function useApiHealth() {
  return useQuery<HealthDto, ApiError>({
    queryKey: ["api-health"],
    queryFn: ({ signal }) => apiRequest<HealthDto>("/health", { signal }),
    refetchInterval: 30_000,
    retry: 1,
  });
}
