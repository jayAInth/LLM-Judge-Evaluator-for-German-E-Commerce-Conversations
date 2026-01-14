import { useOverviewStats, useTimeseries } from "@/hooks/useStats"
import { useEvaluations } from "@/hooks/useEvaluations"
import { StatsCards } from "@/components/dashboard/StatsCards"
import { TrendChart } from "@/components/dashboard/TrendChart"
import { CategoryChart } from "@/components/dashboard/CategoryChart"
import { RecentEvaluations } from "@/components/dashboard/RecentEvaluations"

export function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useOverviewStats()
  const { data: timeseries, isLoading: timeseriesLoading } = useTimeseries(7)
  const { data: evaluationsData, isLoading: evaluationsLoading } = useEvaluations({
    page: 1,
    page_size: 10,
  })

  return (
    <div className="space-y-6">
      <StatsCards stats={stats} isLoading={statsLoading} />

      <div className="grid gap-6 md:grid-cols-2">
        <TrendChart data={timeseries} isLoading={timeseriesLoading} />
        <CategoryChart
          data={stats?.category_distribution}
          isLoading={statsLoading}
        />
      </div>

      <RecentEvaluations
        evaluations={evaluationsData?.items}
        isLoading={evaluationsLoading}
      />
    </div>
  )
}
