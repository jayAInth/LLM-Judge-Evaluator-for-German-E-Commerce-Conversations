import type { DimensionScore } from "@/lib/types"
import { cn } from "@/lib/utils"

interface DimensionScoresProps {
  scores: DimensionScore[] | Record<string, { score: number; weight: number; reasoning?: string }>
}

export function DimensionScores({ scores }: DimensionScoresProps) {
  // Convert object format to array format if needed
  const scoresArray: DimensionScore[] = Array.isArray(scores)
    ? scores
    : Object.entries(scores || {}).map(([name, data]) => ({
        name,
        score: data.score ?? 0,
        weight: data.weight ?? 0,
        feedback: data.reasoning,
      }))

  if (scoresArray.length === 0) {
    return <p className="text-sm text-muted-foreground">No dimension scores available</p>
  }

  return (
    <div className="space-y-3">
      {scoresArray.map((dimension) => (
        <div key={dimension.name} className="space-y-1">
          <div className="flex justify-between text-sm">
            <span className="font-medium">{dimension.name}</span>
            <span className="text-muted-foreground">
              {(dimension.score ?? 0).toFixed(1)}/10
              <span className="text-xs ml-1">({((dimension.weight ?? 0) * 100).toFixed(0)}%)</span>
            </span>
          </div>
          <div className="h-2 bg-secondary rounded-full overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all",
                (dimension.score ?? 0) >= 8
                  ? "bg-green-500"
                  : (dimension.score ?? 0) >= 6
                  ? "bg-yellow-500"
                  : (dimension.score ?? 0) >= 4
                  ? "bg-orange-500"
                  : "bg-red-500"
              )}
              style={{ width: `${(dimension.score ?? 0) * 10}%` }}
            />
          </div>
          {dimension.feedback && (
            <p className="text-xs text-muted-foreground">{dimension.feedback}</p>
          )}
        </div>
      ))}
    </div>
  )
}
