import { Link } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import type { Evaluation } from "@/lib/types"
import { formatDate, formatScore, getScoreColor } from "@/lib/utils"

interface RecentEvaluationsProps {
  evaluations?: Evaluation[]
  isLoading: boolean
}

export function RecentEvaluations({
  evaluations,
  isLoading,
}: RecentEvaluationsProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Evaluations</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Recent Evaluations</CardTitle>
        <Link
          to="/evaluations"
          className="text-sm text-primary hover:underline"
        >
          View all
        </Link>
      </CardHeader>
      <CardContent>
        {!evaluations?.length ? (
          <p className="text-center text-muted-foreground py-8">
            No evaluations yet
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>Flags</TableHead>
                <TableHead>Date</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {evaluations.slice(0, 10).map((evaluation) => (
                <TableRow key={evaluation.id}>
                  <TableCell className="font-mono text-xs">
                    <Link
                      to={`/evaluations?id=${evaluation.id}`}
                      className="hover:underline"
                    >
                      {evaluation.conversation_id.slice(0, 8)}...
                    </Link>
                  </TableCell>
                  <TableCell>
                    <span className={getScoreColor(evaluation.overall_score)}>
                      {formatScore(evaluation.overall_score)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {evaluation.critical_error && (
                        <Badge variant="error">Error</Badge>
                      )}
                      {evaluation.compliance_issue && (
                        <Badge variant="warning">Compliance</Badge>
                      )}
                      {!evaluation.critical_error &&
                        !evaluation.compliance_issue && (
                          <Badge variant="success">OK</Badge>
                        )}
                    </div>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDate(evaluation.evaluated_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}
