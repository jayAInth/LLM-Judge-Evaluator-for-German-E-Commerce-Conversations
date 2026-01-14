import type {
  Conversation,
  Evaluation,
  EvaluationJob,
  HumanAnnotation,
  MetaEvaluationMetrics,
  OverviewStats,
  TimeseriesDataPoint,
  Rubric,
  PaginatedResponse,
} from "./types"

const API_BASE = "/api/v1"

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  return response.json()
}

// Health
export async function getHealth(): Promise<{ status: string; components: Record<string, string> }> {
  return fetchApi("/health")
}

// Conversations
export async function getConversations(params?: {
  page?: number
  page_size?: number
  category?: string
  search?: string
}): Promise<PaginatedResponse<Conversation>> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set("page", params.page.toString())
  if (params?.page_size) searchParams.set("page_size", params.page_size.toString())
  if (params?.category) searchParams.set("category", params.category)
  if (params?.search) searchParams.set("search", params.search)

  const query = searchParams.toString()
  return fetchApi(`/conversations${query ? `?${query}` : ""}`)
}

export async function getConversation(id: string): Promise<Conversation> {
  return fetchApi(`/conversations/${id}`)
}

export async function createConversation(data: {
  external_id?: string
  category: string
  messages: { role: string; content: string }[]
  metadata?: Record<string, unknown>
  conversation_timestamp?: string
}): Promise<Conversation> {
  return fetchApi("/conversations", {
    method: "POST",
    body: JSON.stringify({
      ...data,
      conversation_timestamp: data.conversation_timestamp || new Date().toISOString(),
    }),
  })
}

export async function uploadConversationsBatch(
  conversations: Array<{
    external_id?: string
    category: string
    messages: { role: string; content: string }[]
    metadata?: Record<string, unknown>
    conversation_timestamp?: string
  }>
): Promise<{ created: number; failed: number; errors: string[] }> {
  const now = new Date().toISOString()
  const conversationsWithTimestamp = conversations.map(c => ({
    ...c,
    conversation_timestamp: c.conversation_timestamp || now,
  }))
  return fetchApi("/conversations/batch", {
    method: "POST",
    body: JSON.stringify({ conversations: conversationsWithTimestamp }),
  })
}

export async function deleteConversation(id: string): Promise<void> {
  await fetchApi(`/conversations/${id}`, { method: "DELETE" })
}

// Evaluations
export async function deleteEvaluation(id: string): Promise<void> {
  await fetchApi(`/evaluations/${id}`, { method: "DELETE" })
}

// Evaluations
export async function getEvaluations(params?: {
  page?: number
  page_size?: number
  category?: string
  min_score?: number
  max_score?: number
  critical_error?: boolean
  compliance_issue?: boolean
}): Promise<PaginatedResponse<Evaluation>> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set("page", params.page.toString())
  if (params?.page_size) searchParams.set("page_size", params.page_size.toString())
  if (params?.category) searchParams.set("category", params.category)
  if (params?.min_score !== undefined) searchParams.set("min_score", params.min_score.toString())
  if (params?.max_score !== undefined) searchParams.set("max_score", params.max_score.toString())
  if (params?.critical_error !== undefined) searchParams.set("critical_error", params.critical_error.toString())
  if (params?.compliance_issue !== undefined) searchParams.set("compliance_issue", params.compliance_issue.toString())

  const query = searchParams.toString()
  return fetchApi(`/evaluations${query ? `?${query}` : ""}`)
}

export async function getEvaluation(id: string): Promise<Evaluation> {
  return fetchApi(`/evaluations/${id}`)
}

export async function runSingleEvaluation(conversationId: string, rubricId?: string): Promise<Evaluation> {
  return fetchApi("/evaluations/single", {
    method: "POST",
    body: JSON.stringify({
      conversation_id: conversationId,
      rubric_id: rubricId,
    }),
  })
}

export async function runInlineEvaluation(data: {
  category: string
  messages: { role: string; content: string }[]
}): Promise<Evaluation> {
  return fetchApi("/evaluations/inline", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

// Jobs
export async function getJobs(params?: {
  page?: number
  page_size?: number
  status?: string
}): Promise<PaginatedResponse<EvaluationJob>> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set("page", params.page.toString())
  if (params?.page_size) searchParams.set("page_size", params.page_size.toString())
  if (params?.status) searchParams.set("status", params.status)

  const query = searchParams.toString()
  return fetchApi(`/jobs${query ? `?${query}` : ""}`)
}

export async function getJob(id: string): Promise<EvaluationJob> {
  return fetchApi(`/jobs/${id}`)
}

export async function getJobProgress(id: string): Promise<{
  progress_percent: number
  completed_count: number
  failed_count: number
  estimated_completion?: string
}> {
  return fetchApi(`/jobs/${id}/progress`)
}

export async function createJob(data: {
  conversation_ids?: string[]
  category_filter?: string
  date_from?: string
  date_to?: string
}): Promise<EvaluationJob> {
  return fetchApi("/jobs", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function cancelJob(id: string): Promise<void> {
  await fetchApi(`/jobs/${id}/cancel`, { method: "POST" })
}

// Annotations
export async function getAnnotations(params?: {
  page?: number
  page_size?: number
  evaluation_id?: string
}): Promise<PaginatedResponse<HumanAnnotation>> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set("page", params.page.toString())
  if (params?.page_size) searchParams.set("page_size", params.page_size.toString())
  if (params?.evaluation_id) searchParams.set("evaluation_id", params.evaluation_id)

  const query = searchParams.toString()
  return fetchApi(`/annotations${query ? `?${query}` : ""}`)
}

export async function createAnnotation(data: {
  evaluation_id: string
  annotator_id: string
  overall_score: number
  dimension_scores: { name: string; score: number }[]
  notes?: string
}): Promise<HumanAnnotation> {
  return fetchApi("/annotations", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

// Statistics
export async function getOverviewStats(): Promise<OverviewStats> {
  return fetchApi("/stats/overview")
}

export async function getTimeseries(params?: {
  days?: number
}): Promise<TimeseriesDataPoint[]> {
  const searchParams = new URLSearchParams()
  if (params?.days) searchParams.set("days", params.days.toString())
  searchParams.set("metric", "avg_score")

  const query = searchParams.toString()
  const response = await fetchApi<{ metric: string; granularity: string; data: Array<{ timestamp: string; value: number; count: number }> }>(`/stats/timeseries${query ? `?${query}` : ""}`)

  // Transform API response to frontend format
  return (response.data || []).map(point => ({
    date: point.timestamp,
    average_score: point.value,
    evaluation_count: point.count,
  }))
}

// Meta-Evaluation
export async function getMetaEvaluation(): Promise<MetaEvaluationMetrics> {
  return fetchApi("/meta-evaluation")
}

// Rubrics
export async function getRubrics(): Promise<Rubric[]> {
  return fetchApi("/rubrics")
}

export async function getRubric(id: string): Promise<Rubric> {
  return fetchApi(`/rubrics/${id}`)
}

export async function createRubric(data: {
  name: string
  version: string
  description?: string
  dimensions: {
    name: string
    weight: number
    description: string
    scoring_criteria: string[]
  }[]
}): Promise<Rubric> {
  return fetchApi("/rubrics", {
    method: "POST",
    body: JSON.stringify(data),
  })
}
