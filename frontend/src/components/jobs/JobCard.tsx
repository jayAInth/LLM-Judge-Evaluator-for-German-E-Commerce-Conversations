import { Clock, CheckCircle2, XCircle, Loader2, Ban } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import type { EvaluationJob } from "@/lib/types"
import { formatDate, getStatusColor, getCategoryLabel } from "@/lib/utils"
import { useCancelJob, useJobProgress } from "@/hooks/useJobs"

interface JobCardProps {
  job: EvaluationJob
}

const statusIcons = {
  PENDING: Clock,
  RUNNING: Loader2,
  COMPLETED: CheckCircle2,
  FAILED: XCircle,
  CANCELLED: Ban,
}

export function JobCard({ job }: JobCardProps) {
  const isActive = job.status === "RUNNING" || job.status === "PENDING"
  const { data: progress } = useJobProgress(job.id, job.status === "RUNNING")
  const cancelMutation = useCancelJob()

  const StatusIcon = statusIcons[job.status]
  const currentProgress = progress?.progress_percent ?? job.progress_percent

  const handleCancel = async () => {
    if (confirm("Are you sure you want to cancel this job?")) {
      await cancelMutation.mutateAsync(job.id)
    }
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-base font-mono">
              {job.id.slice(0, 12)}...
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              {formatDate(job.created_at)}
            </p>
          </div>
          <Badge className={getStatusColor(job.status)}>
            <StatusIcon
              className={`h-3 w-3 mr-1 ${
                job.status === "RUNNING" ? "animate-spin" : ""
              }`}
            />
            {job.status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {job.category_filter && (
          <div className="text-sm">
            <span className="text-muted-foreground">Category: </span>
            {getCategoryLabel(job.category_filter)}
          </div>
        )}

        <div>
          <div className="flex justify-between text-sm mb-1">
            <span>Progress</span>
            <span>
              {progress?.completed_count ?? job.completed_count} /{" "}
              {job.total_conversations}
            </span>
          </div>
          <Progress value={currentProgress} className="h-2" />
        </div>

        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground">Total</p>
            <p className="font-semibold">{job.total_conversations}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Completed</p>
            <p className="font-semibold text-green-500">
              {progress?.completed_count ?? job.completed_count}
            </p>
          </div>
          <div>
            <p className="text-muted-foreground">Failed</p>
            <p className="font-semibold text-red-500">
              {progress?.failed_count ?? job.failed_count}
            </p>
          </div>
        </div>

        {progress?.estimated_completion && job.status === "RUNNING" && (
          <p className="text-sm text-muted-foreground">
            ETA: {formatDate(progress.estimated_completion)}
          </p>
        )}

        {job.error_message && (
          <p className="text-sm text-destructive">{job.error_message}</p>
        )}

        {isActive && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleCancel}
            disabled={cancelMutation.isPending}
            className="w-full"
          >
            Cancel Job
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
