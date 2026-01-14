import { useState } from "react"
import { Eye, AlertTriangle, Shield, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Slider } from "@/components/ui/slider"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { EvaluationDetail } from "@/components/evaluations/EvaluationDetail"
import { useEvaluations, useDeleteEvaluation } from "@/hooks/useEvaluations"
import type { Evaluation } from "@/lib/types"
import { formatDate, formatScore, getScoreColor } from "@/lib/utils"

const CATEGORIES = [
  { value: "all", label: "All Categories" },
  { value: "retoure", label: "Retoure" },
  { value: "beschwerde", label: "Beschwerde" },
  { value: "produktanfrage", label: "Produktanfrage" },
  { value: "lieferung", label: "Lieferung" },
  { value: "zahlung", label: "Zahlung" },
  { value: "konto", label: "Konto" },
  { value: "allgemein", label: "Allgemein" },
]

export function EvaluationsPage() {
  const [page, setPage] = useState(1)
  const [category, setCategory] = useState("all")
  const [scoreRange, setScoreRange] = useState([0, 10])
  const [showCriticalOnly, setShowCriticalOnly] = useState(false)
  const [showComplianceOnly, setShowComplianceOnly] = useState(false)
  const [selectedEvaluation, setSelectedEvaluation] =
    useState<Evaluation | null>(null)

  const { data, isLoading } = useEvaluations({
    page,
    page_size: 20,
    category: category !== "all" ? category : undefined,
    min_score: scoreRange[0],
    max_score: scoreRange[1],
    critical_error: showCriticalOnly || undefined,
    compliance_issue: showComplianceOnly || undefined,
  })

  const deleteMutation = useDeleteEvaluation()

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this evaluation?")) {
      await deleteMutation.mutateAsync(id)
    }
  }

  return (
    <div className="space-y-6">
      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <Label>Category</Label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CATEGORIES.map((cat) => (
                    <SelectItem key={cat.value} value={cat.value}>
                      {cat.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="col-span-2">
              <Label>
                Score Range: {scoreRange[0]} - {scoreRange[1]}
              </Label>
              <Slider
                value={scoreRange}
                onValueChange={setScoreRange}
                min={0}
                max={10}
                step={0.5}
                className="mt-2"
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label>Flags</Label>
              <div className="flex gap-2">
                <Button
                  variant={showCriticalOnly ? "default" : "outline"}
                  size="sm"
                  onClick={() => setShowCriticalOnly(!showCriticalOnly)}
                >
                  <AlertTriangle className="h-3 w-3 mr-1" />
                  Critical
                </Button>
                <Button
                  variant={showComplianceOnly ? "default" : "outline"}
                  size="sm"
                  onClick={() => setShowComplianceOnly(!showComplianceOnly)}
                >
                  <Shield className="h-3 w-3 mr-1" />
                  Compliance
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      <Card>
        <CardHeader>
          <CardTitle>
            Evaluations
            {data && (
              <span className="text-muted-foreground font-normal ml-2">
                ({data.total} total)
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : !data?.items.length ? (
            <p className="text-center text-muted-foreground py-8">
              No evaluations found
            </p>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Conversation</TableHead>
                    <TableHead>Score</TableHead>
                    <TableHead>Flags</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((evaluation) => (
                    <TableRow key={evaluation.id}>
                      <TableCell className="font-mono text-xs">
                        {evaluation.conversation_id.slice(0, 12)}...
                      </TableCell>
                      <TableCell>
                        <span
                          className={`font-semibold ${getScoreColor(
                            evaluation.overall_score
                          )}`}
                        >
                          {formatScore(evaluation.overall_score)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          {evaluation.critical_error && (
                            <Badge variant="error">
                              <AlertTriangle className="h-3 w-3 mr-1" />
                              Error
                            </Badge>
                          )}
                          {evaluation.compliance_issue && (
                            <Badge variant="warning">
                              <Shield className="h-3 w-3 mr-1" />
                              Compliance
                            </Badge>
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
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setSelectedEvaluation(evaluation)}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(evaluation.id)}
                            disabled={deleteMutation.isPending}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {data.total_pages > 1 && (
                <div className="flex justify-center gap-2 mt-4">
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
        </CardContent>
      </Card>

      {selectedEvaluation && (
        <EvaluationDetail
          evaluation={selectedEvaluation}
          onClose={() => setSelectedEvaluation(null)}
        />
      )}
    </div>
  )
}
