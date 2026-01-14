import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Eye, CheckCircle2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { getRubrics } from "@/lib/api"
import type { Rubric } from "@/lib/types"
import { formatDate } from "@/lib/utils"

export function RubricsPage() {
  const [selectedRubric, setSelectedRubric] = useState<Rubric | null>(null)

  const { data: rubrics, isLoading } = useQuery({
    queryKey: ["rubrics"],
    queryFn: getRubrics,
  })

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-48 w-full" />
        ))}
      </div>
    )
  }

  if (!rubrics?.length) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-muted-foreground">
            No rubrics configured. Contact your administrator to set up
            evaluation rubrics.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {rubrics.map((rubric) => (
          <Card key={rubric.id}>
            <CardHeader>
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle className="text-lg">{rubric.name}</CardTitle>
                  <CardDescription>Version {rubric.version}</CardDescription>
                </div>
                {rubric.is_active && (
                  <Badge variant="success" className="flex items-center gap-1">
                    <CheckCircle2 className="h-3 w-3" />
                    Active
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {rubric.description && (
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {rubric.description}
                </p>
              )}

              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Dimensions</span>
                <span className="font-medium">{rubric.dimensions.length}</span>
              </div>

              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Created</span>
                <span>{formatDate(rubric.created_at)}</span>
              </div>

              <Button
                variant="outline"
                className="w-full"
                onClick={() => setSelectedRubric(rubric)}
              >
                <Eye className="mr-2 h-4 w-4" />
                View Details
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog
        open={!!selectedRubric}
        onOpenChange={() => setSelectedRubric(null)}
      >
        <DialogContent className="max-w-2xl max-h-[80vh]">
          <DialogHeader>
            <DialogTitle>
              {selectedRubric?.name} v{selectedRubric?.version}
            </DialogTitle>
          </DialogHeader>

          <ScrollArea className="max-h-[60vh]">
            <div className="space-y-6 pr-4">
              {selectedRubric?.description && (
                <p className="text-muted-foreground">
                  {selectedRubric.description}
                </p>
              )}

              <Separator />

              <div>
                <h3 className="font-semibold mb-4">Dimensions</h3>
                <div className="space-y-4">
                  {selectedRubric?.dimensions.map((dimension, index) => (
                    <Card key={index}>
                      <CardHeader className="pb-2">
                        <div className="flex justify-between items-start">
                          <CardTitle className="text-base">
                            {dimension.name}
                          </CardTitle>
                          <Badge variant="secondary">
                            Weight: {(dimension.weight * 100).toFixed(0)}%
                          </Badge>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <p className="text-sm text-muted-foreground">
                          {dimension.description}
                        </p>

                        {dimension.scoring_criteria.length > 0 && (
                          <div>
                            <p className="text-sm font-medium mb-2">
                              Scoring Criteria:
                            </p>
                            <ul className="text-sm space-y-1">
                              {dimension.scoring_criteria.map(
                                (criteria, idx) => (
                                  <li
                                    key={idx}
                                    className="flex items-start gap-2"
                                  >
                                    <span className="text-primary">•</span>
                                    <span className="text-muted-foreground">
                                      {criteria}
                                    </span>
                                  </li>
                                )
                              )}
                            </ul>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            </div>
          </ScrollArea>
        </DialogContent>
      </Dialog>
    </>
  )
}
