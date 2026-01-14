import { X, AlertTriangle, Shield, Phone } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { DimensionScores } from "./DimensionScores"
import { ChainOfThought } from "./ChainOfThought"
import type { Evaluation } from "@/lib/types"
import { formatDate, formatScore, getScoreColor, getScoreBgColor } from "@/lib/utils"

interface EvaluationDetailProps {
  evaluation: Evaluation | null
  onClose: () => void
}

export function EvaluationDetail({
  evaluation,
  onClose,
}: EvaluationDetailProps) {
  if (!evaluation) return null

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/50"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="fixed inset-y-0 right-0 z-50 w-full max-w-lg border-l bg-background shadow-lg">
      <div className="flex h-16 items-center justify-between border-b px-4">
        <div>
          <h2 className="font-semibold">Evaluation Details</h2>
          <p className="text-sm text-muted-foreground font-mono">
            {evaluation.id.slice(0, 12)}...
          </p>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X className="h-5 w-5" />
        </Button>
      </div>

      <ScrollArea className="h-[calc(100vh-4rem)]">
        <div className="p-4 space-y-6">
          {/* Overall Score */}
          <div
            className={`p-6 rounded-lg text-center ${getScoreBgColor(
              evaluation.overall_score
            )}`}
          >
            <p className="text-sm text-muted-foreground mb-1">Overall Score</p>
            <p
              className={`text-5xl font-bold ${getScoreColor(
                evaluation.overall_score
              )}`}
            >
              {formatScore(evaluation.overall_score)}
            </p>
            <p className="text-sm text-muted-foreground mt-1">out of 10</p>
          </div>

          {/* Flags */}
          {(evaluation.critical_error ||
            evaluation.compliance_issue ||
            evaluation.escalation_needed) && (
            <div className="flex flex-wrap gap-2">
              {evaluation.critical_error && (
                <Badge variant="error" className="flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3" />
                  Critical Error
                </Badge>
              )}
              {evaluation.compliance_issue && (
                <Badge variant="warning" className="flex items-center gap-1">
                  <Shield className="h-3 w-3" />
                  Compliance Issue
                </Badge>
              )}
              {evaluation.escalation_needed && (
                <Badge variant="secondary" className="flex items-center gap-1">
                  <Phone className="h-3 w-3" />
                  Escalation Needed
                </Badge>
              )}
            </div>
          )}

          <Separator />

          {/* Dimension Scores */}
          <div>
            <h3 className="font-medium mb-4">Dimension Scores</h3>
            <DimensionScores scores={evaluation.dimension_scores} />
          </div>

          <Separator />

          {/* Chain of Thought */}
          <ChainOfThought content={evaluation.chain_of_thought} />

          <Separator />

          {/* Metadata */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Evaluated</p>
              <p>{formatDate(evaluation.evaluated_at)}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Conversation</p>
              <p className="font-mono text-xs">
                {evaluation.conversation_id.slice(0, 12)}...
              </p>
            </div>
            {evaluation.model_name && (
              <div>
                <p className="text-muted-foreground">Model</p>
                <p className="text-xs">{evaluation.model_name}</p>
              </div>
            )}
            {evaluation.rubric_version && (
              <div>
                <p className="text-muted-foreground">Rubric Version</p>
                <p>{evaluation.rubric_version}</p>
              </div>
            )}
            {evaluation.job_id && (
              <div>
                <p className="text-muted-foreground">Job ID</p>
                <p className="font-mono text-xs">
                  {evaluation.job_id.slice(0, 12)}...
                </p>
              </div>
            )}
          </div>
        </div>
      </ScrollArea>
      </div>
    </>
  )
}
