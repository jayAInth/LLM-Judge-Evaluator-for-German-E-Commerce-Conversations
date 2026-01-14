export interface Message {
  role: "customer" | "agent"
  content: string
  timestamp?: string
}

export interface Conversation {
  id: string
  external_id?: string
  category: string
  messages: Message[]
  metadata?: Record<string, unknown>
  created_at: string
  conversation_timestamp?: string
  pii_redacted: boolean
  evaluated?: boolean
}

export interface DimensionScore {
  name: string
  score: number
  weight: number
  feedback?: string
}

export interface ChainOfThought {
  context_analysis: string
  response_analysis: string
  legal_check: string
  language_assessment: string
}

export interface Evaluation {
  id: string
  conversation_id: string
  job_id?: string
  overall_score: number
  dimension_scores: DimensionScore[]
  chain_of_thought?: ChainOfThought
  critical_error: boolean
  compliance_issue: boolean
  escalation_needed: boolean
  evaluated_at: string
  model_name?: string
  rubric_version?: string
}

export type JobStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED"

export interface EvaluationJob {
  id: string
  status: JobStatus
  total_conversations: number
  completed_count: number
  failed_count: number
  progress_percent: number
  category_filter?: string
  created_at: string
  started_at?: string
  completed_at?: string
  estimated_completion?: string
  error_message?: string
}

export interface HumanAnnotation {
  id: string
  evaluation_id: string
  annotator_id: string
  overall_score: number
  dimension_scores: DimensionScore[]
  notes?: string
  created_at: string
}

export interface MetaEvaluationMetrics {
  total_annotations: number
  pearson_correlation: number
  spearman_correlation: number
  kendall_tau: number
  cohens_kappa: number
  mae: number
  rmse: number
  per_dimension_correlation: Record<string, number>
  calibration_needed: boolean
  recommendations: string[]
}

export interface OverviewStats {
  total_conversations: number
  total_evaluations: number
  evaluations_today: number
  average_score: number
  median_score: number
  active_jobs: number
  critical_errors_count: number
  compliance_issues_count: number
  category_distribution: Record<string, number>
  score_distribution: Record<string, number>
}

export interface TimeseriesDataPoint {
  date: string
  average_score: number
  evaluation_count: number
}

export interface Rubric {
  id: string
  name: string
  version: string
  description?: string
  dimensions: RubricDimension[]
  is_active: boolean
  created_at: string
}

export interface RubricDimension {
  name: string
  weight: number
  description: string
  scoring_criteria: string[]
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface ApiError {
  detail: string
  status_code: number
}
