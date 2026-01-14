import { useQuery } from "@tanstack/react-query"
import { getOverviewStats, getTimeseries } from "@/lib/api"

export function useOverviewStats() {
  return useQuery({
    queryKey: ["stats", "overview"],
    queryFn: getOverviewStats,
    staleTime: 30000,
  })
}

export function useTimeseries(days = 7) {
  return useQuery({
    queryKey: ["stats", "timeseries", days],
    queryFn: () => getTimeseries({ days }),
    staleTime: 60000,
  })
}
