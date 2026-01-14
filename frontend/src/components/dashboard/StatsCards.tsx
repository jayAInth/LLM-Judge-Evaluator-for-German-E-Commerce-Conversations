import {
  MessageSquare,
  ClipboardCheck,
  TrendingUp,
  Briefcase,
  AlertTriangle,
  Shield,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import type { OverviewStats } from "@/lib/types"
import { formatScore } from "@/lib/utils"

interface StatsCardsProps {
  stats?: OverviewStats
  isLoading: boolean
}

export function StatsCards({ stats, isLoading }: StatsCardsProps) {
  const cards = [
    {
      title: "Total Conversations",
      value: stats?.total_conversations ?? 0,
      icon: MessageSquare,
      description: "All uploaded conversations",
    },
    {
      title: "Evaluations Today",
      value: stats?.evaluations_today ?? 0,
      icon: ClipboardCheck,
      description: "Completed today",
    },
    {
      title: "Average Score",
      value: stats?.average_score ? formatScore(stats.average_score) : "N/A",
      icon: TrendingUp,
      description: "Overall quality score",
    },
    {
      title: "Active Jobs",
      value: stats?.active_jobs ?? 0,
      icon: Briefcase,
      description: "Running batch jobs",
    },
    {
      title: "Critical Errors",
      value: stats?.critical_errors_count ?? 0,
      icon: AlertTriangle,
      description: "Evaluations with errors",
      variant: (stats?.critical_errors_count ?? 0) > 0 ? "destructive" : "default",
    },
    {
      title: "Compliance Issues",
      value: stats?.compliance_issues_count ?? 0,
      icon: Shield,
      description: "Potential compliance problems",
      variant: (stats?.compliance_issues_count ?? 0) > 0 ? "warning" : "default",
    },
  ]

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-4" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-16 mb-1" />
              <Skeleton className="h-3 w-32" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
      {cards.map((card) => (
        <Card key={card.title}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{card.title}</CardTitle>
            <card.icon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{card.value}</div>
            <p className="text-xs text-muted-foreground">{card.description}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
