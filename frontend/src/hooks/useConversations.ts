import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  getConversations,
  getConversation,
  createConversation,
  uploadConversationsBatch,
  deleteConversation,
} from "@/lib/api"

export function useConversations(params?: {
  page?: number
  page_size?: number
  category?: string
  search?: string
}) {
  return useQuery({
    queryKey: ["conversations", params],
    queryFn: () => getConversations(params),
  })
}

export function useConversation(id: string) {
  return useQuery({
    queryKey: ["conversation", id],
    queryFn: () => getConversation(id),
    enabled: !!id,
  })
}

export function useCreateConversation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: createConversation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] })
      queryClient.invalidateQueries({ queryKey: ["stats"] })
    },
  })
}

export function useUploadConversations() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: uploadConversationsBatch,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] })
      queryClient.invalidateQueries({ queryKey: ["stats"] })
    },
  })
}

export function useDeleteConversation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: deleteConversation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] })
      queryClient.invalidateQueries({ queryKey: ["stats"] })
    },
  })
}
