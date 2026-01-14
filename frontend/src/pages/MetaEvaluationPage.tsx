import { useQuery } from "@tanstack/react-query"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
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
import { getMetaEvaluation } from "@/lib/api"
import { AlertTriangle, CheckCircle2 } from "lucide-react"

export function MetaEvaluationPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["meta-evaluation"],
    queryFn: getMetaEvaluation,
  })

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-muted-foreground">
            No meta-evaluation data available. Add human annotations to compare
            with LLM judge scores.
          </p>
        </CardContent>
      </Card>
    )
  }

  const metrics = [
    {
      label: "Pearson Correlation",
      value: data.pearson_correlation,
      description: "Linear correlation",
      target: 0.87,
    },
    {
      label: "Spearman Correlation",
      value: data.spearman_correlation,
      description: "Rank correlation",
      target: 0.85,
    },
    {
      label: "Kendall's Tau",
      value: data.kendall_tau,
      description: "Ordinal association",
      target: 0.75,
    },
    {
      label: "Cohen's Kappa",
      value: data.cohens_kappa,
      description: "Agreement measure",
      target: 0.7,
    },
  ]

  const errorMetrics = [
    { label: "MAE", value: data.mae, description: "Mean Absolute Error" },
    { label: "RMSE", value: data.rmse, description: "Root Mean Square Error" },
  ]

  return (
    <div className="space-y-6">
      {/* Calibration Status */}
      <Card
        className={
          data.calibration_needed
            ? "border-yellow-500/50 bg-yellow-500/5"
            : "border-green-500/50 bg-green-500/5"
        }
      >
        <CardContent className="flex items-center gap-4 py-4">
          {data.calibration_needed ? (
            <>
              <AlertTriangle className="h-8 w-8 text-yellow-500" />
              <div>
                <h3 className="font-semibold">Calibration Recommended</h3>
                <p className="text-sm text-muted-foreground">
                  Judge-human correlation is below target. Consider adjusting
                  prompts or rubric weights.
                </p>
              </div>
            </>
          ) : (
            <>
              <CheckCircle2 className="h-8 w-8 text-green-500" />
              <div>
                <h3 className="font-semibold">Judge Well-Calibrated</h3>
                <p className="text-sm text-muted-foreground">
                  LLM judge scores correlate well with human expert annotations.
                </p>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Correlation Metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {metrics.map((metric) => (
          <Card key={metric.label}>
            <CardHeader className="pb-2">
              <CardDescription>{metric.description}</CardDescription>
              <CardTitle className="text-base">{metric.label}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-end justify-between">
                <span
                  className={`text-3xl font-bold ${
                    (metric.value ?? 0) >= metric.target
                      ? "text-green-500"
                      : "text-yellow-500"
                  }`}
                >
                  {metric.value?.toFixed(3) ?? "N/A"}
                </span>
                <Badge
                  variant={
                    (metric.value ?? 0) >= metric.target ? "success" : "warning"
                  }
                >
                  Target: {metric.target}
                </Badge>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Error Metrics */}
      <div className="grid gap-4 md:grid-cols-2">
        {errorMetrics.map((metric) => (
          <Card key={metric.label}>
            <CardHeader className="pb-2">
              <CardDescription>{metric.description}</CardDescription>
              <CardTitle className="text-base">{metric.label}</CardTitle>
            </CardHeader>
            <CardContent>
              <span className="text-3xl font-bold">{metric.value?.toFixed(3) ?? "N/A"}</span>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Per-Dimension Correlation */}
      <Card>
        <CardHeader>
          <CardTitle>Per-Dimension Correlation</CardTitle>
          <CardDescription>
            Pearson correlation for each evaluation dimension
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Dimension</TableHead>
                <TableHead>Correlation</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {Object.entries(data.per_dimension_correlation ?? {}).map(
                ([dimension, correlation]) => (
                  <TableRow key={dimension}>
                    <TableCell className="font-medium">{dimension}</TableCell>
                    <TableCell
                      className={
                        (correlation ?? 0) >= 0.8
                          ? "text-green-500"
                          : (correlation ?? 0) >= 0.6
                          ? "text-yellow-500"
                          : "text-red-500"
                      }
                    >
                      {(correlation as number)?.toFixed(3) ?? "N/A"}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          (correlation ?? 0) >= 0.8
                            ? "success"
                            : (correlation ?? 0) >= 0.6
                            ? "warning"
                            : "error"
                        }
                      >
                        {(correlation ?? 0) >= 0.8
                          ? "Good"
                          : (correlation ?? 0) >= 0.6
                          ? "Fair"
                          : "Poor"}
                      </Badge>
                    </TableCell>
                  </TableRow>
                )
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Recommendations */}
      {data.recommendations?.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Recommendations</CardTitle>
            <CardDescription>
              Suggestions for improving judge calibration
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {data.recommendations.map((rec, index) => (
                <li key={index} className="flex items-start gap-2">
                  <span className="text-primary">•</span>
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Annotations Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Annotations Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-bold">{data.total_annotations}</p>
          <p className="text-sm text-muted-foreground">
            Total human annotations collected
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
