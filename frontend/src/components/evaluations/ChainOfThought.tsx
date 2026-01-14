import { useState } from "react"
import { ChevronDown, ChevronRight, Brain } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import type { ChainOfThought as ChainOfThoughtType } from "@/lib/types"

interface ChainOfThoughtProps {
  content?: ChainOfThoughtType
}

export function ChainOfThought({ content }: ChainOfThoughtProps) {
  const [open, setOpen] = useState(false)

  if (!content) return null

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger asChild>
        <Button variant="ghost" className="w-full justify-start p-0 h-auto">
          <div className="flex items-center gap-2 py-2">
            {open ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
            <Brain className="h-4 w-4 text-primary" />
            <span className="font-medium">Chain of Thought Analysis</span>
          </div>
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="mt-2 space-y-4">
          <div className="p-4 bg-muted rounded-lg">
            <h4 className="text-sm font-medium mb-2">Context Analysis</h4>
            <p className="text-sm whitespace-pre-wrap">{content.context_analysis}</p>
          </div>
          <div className="p-4 bg-muted rounded-lg">
            <h4 className="text-sm font-medium mb-2">Response Analysis</h4>
            <p className="text-sm whitespace-pre-wrap">{content.response_analysis}</p>
          </div>
          <div className="p-4 bg-muted rounded-lg">
            <h4 className="text-sm font-medium mb-2">Legal Check</h4>
            <p className="text-sm whitespace-pre-wrap">{content.legal_check}</p>
          </div>
          <div className="p-4 bg-muted rounded-lg">
            <h4 className="text-sm font-medium mb-2">Language Assessment</h4>
            <p className="text-sm whitespace-pre-wrap">{content.language_assessment}</p>
          </div>
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}
