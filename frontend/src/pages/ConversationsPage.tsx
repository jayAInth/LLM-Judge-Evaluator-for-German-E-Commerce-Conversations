import { useState } from "react"
import { Upload, Search, Eye, Trash2, Play } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
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
import { UploadDialog } from "@/components/conversations/UploadDialog"
import { ConversationDetail } from "@/components/conversations/ConversationDetail"
import { useConversations, useDeleteConversation } from "@/hooks/useConversations"
import { useRunEvaluation } from "@/hooks/useEvaluations"
import type { Conversation } from "@/lib/types"
import { formatDate, getCategoryLabel } from "@/lib/utils"

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

export function ConversationsPage() {
  const [page, setPage] = useState(1)
  const [category, setCategory] = useState("all")
  const [search, setSearch] = useState("")
  const [selectedConversation, setSelectedConversation] =
    useState<Conversation | null>(null)

  const { data, isLoading } = useConversations({
    page,
    page_size: 20,
    category: category !== "all" ? category : undefined,
    search: search || undefined,
  })

  const deleteMutation = useDeleteConversation()
  const evaluateMutation = useRunEvaluation()

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this conversation?")) {
      await deleteMutation.mutateAsync(id)
    }
  }

  const handleEvaluate = async (id: string) => {
    await evaluateMutation.mutateAsync({ conversationId: id })
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row gap-4 justify-between">
        <div className="flex gap-2 flex-1">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger className="w-[180px]">
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

        <UploadDialog>
          <Button>
            <Upload className="mr-2 h-4 w-4" />
            Upload
          </Button>
        </UploadDialog>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>
            Conversations
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
              No conversations found
            </p>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Messages</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((conversation) => (
                    <TableRow key={conversation.id}>
                      <TableCell className="font-mono text-xs">
                        {conversation.external_id ||
                          conversation.id.slice(0, 12)}
                        ...
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">
                          {getCategoryLabel(conversation.category)}
                        </Badge>
                      </TableCell>
                      <TableCell>{conversation.messages.length}</TableCell>
                      <TableCell>
                        {conversation.evaluated ? (
                          <Badge variant="success">Evaluated</Badge>
                        ) : (
                          <Badge variant="secondary">Pending</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDate(conversation.created_at)}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setSelectedConversation(conversation)}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          {!conversation.evaluated && (
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleEvaluate(conversation.id)}
                              disabled={evaluateMutation.isPending}
                            >
                              <Play className="h-4 w-4" />
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(conversation.id)}
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

      {selectedConversation && (
        <ConversationDetail
          conversation={selectedConversation}
          onClose={() => setSelectedConversation(null)}
        />
      )}
    </div>
  )
}
