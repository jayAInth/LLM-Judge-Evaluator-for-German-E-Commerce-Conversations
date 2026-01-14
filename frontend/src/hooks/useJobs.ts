import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { getJobs, getJob, getJobProgress, createJob, cancelJob } from "@/lib/api"

export function useJobs(params?: {
  page?: number
  page_size?: number
  status?: string
}) {
  return useQuery({
    queryKey: ["jobs", params],
    queryFn: () => getJobs(params),
  })
}

export function useJob(id: string) {
  return useQuery({
    queryKey: ["job", id],
    queryFn: () => getJob(id),
    enabled: !!id,
  })
}

export function useJobProgress(id: string, enabled = true) {
  return useQuery({
    queryKey: ["job", id, "progress"],
    queryFn: () => getJobProgress(id),
    enabled: enabled && !!id,
    refetchInterval: (query) => {
      const data = query.state.data
      if (data && data.progress_percent >= 100) {
        return false
      }
      return 2000
    },
  })
}

export function useCreateJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: createJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] })
    },
  })
}

export function useCancelJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: cancelJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] })
    },
  })
}
