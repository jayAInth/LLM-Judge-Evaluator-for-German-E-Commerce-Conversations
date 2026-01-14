import { useState } from "react"
import { Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { JobCard } from "@/components/jobs/JobCard"
import { CreateJobDialog } from "@/components/jobs/CreateJobDialog"
import { useJobs } from "@/hooks/useJobs"

const STATUSES = [
  { value: "all", label: "All Statuses" },
  { value: "PENDING", label: "Pending" },
  { value: "RUNNING", label: "Running" },
  { value: "COMPLETED", label: "Completed" },
  { value: "FAILED", label: "Failed" },
  { value: "CANCELLED", label: "Cancelled" },
]

export function JobsPage() {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState("all")

  const { data, isLoading } = useJobs({
    page,
    page_size: 12,
    status: status !== "all" ? status : undefined,
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row gap-4 justify-between">
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="w-[180px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STATUSES.map((s) => (
              <SelectItem key={s.value} value={s.value}>
                {s.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <CreateJobDialog>
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Create Job
          </Button>
        </CreateJobDialog>
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-64 w-full" />
          ))}
        </div>
      ) : !data?.items.length ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground mb-4">No jobs found</p>
          <CreateJobDialog>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Create Your First Job
            </Button>
          </CreateJobDialog>
        </div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {data.items.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>

          {data.total_pages > 1 && (
            <div className="flex justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                Previous
              </Button>
              <span className="flex items-center px-3 text-sm text-muted-foreground">
                Page {page} of {data.total_pages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => p + 1)}
                disabled={page >= data.total_pages}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
