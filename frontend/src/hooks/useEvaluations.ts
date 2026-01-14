import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  getEvaluations,
  getEvaluation,
  runSingleEvaluation,
  runInlineEvaluation,
  deleteEvaluation,
} from "@/lib/api"

export function useEvaluations(params?: {
  page?: number
  page_size?: number
  category?: string
  min_score?: number
  max_score?: number
  critical_error?: boolean
  compliance_issue?: boolean
}) {
  return useQuery({
    queryKey: ["evaluations", params],
    queryFn: () => getEvaluations(params),
  })
}

export function useEvaluation(id: string) {
  return useQuery({
    queryKey: ["evaluation", id],
    queryFn: () => getEvaluation(id),
    enabled: !!id,
  })
}

export function useRunEvaluation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ conversationId, rubricId }: { conversationId: string; rubricId?: string }) =>
      runSingleEvaluation(conversationId, rubricId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["evaluations"] })
      queryClient.invalidateQueries({ queryKey: ["stats"] })
    },
  })
}

export function useRunInlineEvaluation() {
  return useMutation({
    mutationFn: runInlineEvaluation,
  })
}

export function useDeleteEvaluation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: deleteEvaluation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["evaluations"] })
      queryClient.invalidateQueries({ queryKey: ["stats"] })
    },
  })
}
