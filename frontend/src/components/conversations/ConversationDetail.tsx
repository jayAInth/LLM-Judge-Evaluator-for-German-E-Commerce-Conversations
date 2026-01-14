import { X, User, Bot } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import type { Conversation } from "@/lib/types"
import { formatDate, getCategoryLabel } from "@/lib/utils"

interface ConversationDetailProps {
  conversation: Conversation | null
  onClose: () => void
}

export function ConversationDetail({
  conversation,
  onClose,
}: ConversationDetailProps) {
  if (!conversation) return null

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
          <h2 className="font-semibold">Conversation Details</h2>
          <p className="text-sm text-muted-foreground font-mono">
            {conversation.id.slice(0, 12)}...
          </p>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X className="h-5 w-5" />
        </Button>
      </div>

      <ScrollArea className="h-[calc(100vh-4rem)]">
        <div className="p-4 space-y-4">
          <div className="flex flex-wrap gap-2">
            <Badge>{getCategoryLabel(conversation.category)}</Badge>
            {conversation.pii_redacted && (
              <Badge variant="secondary">PII Redacted</Badge>
            )}
            {conversation.evaluated && (
              <Badge variant="success">Evaluated</Badge>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Created</p>
              <p>{formatDate(conversation.created_at)}</p>
            </div>
            {conversation.external_id && (
              <div>
                <p className="text-muted-foreground">External ID</p>
                <p className="font-mono">{conversation.external_id}</p>
              </div>
            )}
          </div>

          <Separator />

          <div>
            <h3 className="font-medium mb-3">Messages</h3>
            <div className="space-y-3">
              {conversation.messages.map((message, index) => (
                <div
                  key={index}
                  className={`flex gap-3 ${
                    message.role === "agent" ? "flex-row-reverse" : ""
                  }`}
                >
                  <div
                    className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
                      message.role === "customer"
                        ? "bg-secondary"
                        : "bg-primary text-primary-foreground"
                    }`}
                  >
                    {message.role === "customer" ? (
                      <User className="h-4 w-4" />
                    ) : (
                      <Bot className="h-4 w-4" />
                    )}
                  </div>
                  <div
                    className={`flex-1 rounded-lg p-3 ${
                      message.role === "customer"
                        ? "bg-secondary"
                        : "bg-primary/10"
                    }`}
                  >
                    <p className="text-xs text-muted-foreground mb-1 capitalize">
                      {message.role}
                    </p>
                    <p className="text-sm whitespace-pre-wrap">
                      {message.content}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {conversation.metadata &&
            Object.keys(conversation.metadata).length > 0 && (
              <>
                <Separator />
                <div>
                  <h3 className="font-medium mb-2">Metadata</h3>
                  <pre className="text-xs bg-muted p-3 rounded-lg overflow-auto">
                    {JSON.stringify(conversation.metadata, null, 2)}
                  </pre>
                </div>
              </>
            )}
        </div>
      </ScrollArea>
      </div>
    </>
  )
}
