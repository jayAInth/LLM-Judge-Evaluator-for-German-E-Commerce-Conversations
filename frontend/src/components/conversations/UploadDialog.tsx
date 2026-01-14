import { useState, useCallback } from "react"
import { Upload, FileJson, AlertCircle } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useUploadConversations, useCreateConversation } from "@/hooks/useConversations"

const CATEGORIES = [
  { value: "retoure", label: "Retoure" },
  { value: "beschwerde", label: "Beschwerde" },
  { value: "produktanfrage", label: "Produktanfrage" },
  { value: "lieferung", label: "Lieferung" },
  { value: "zahlung", label: "Zahlung" },
  { value: "konto", label: "Konto" },
  { value: "allgemein", label: "Allgemein" },
]

interface UploadDialogProps {
  children: React.ReactNode
}

export function UploadDialog({ children }: UploadDialogProps) {
  const [open, setOpen] = useState(false)
  const [mode, setMode] = useState<"single" | "batch">("single")
  const [category, setCategory] = useState("")
  const [messages, setMessages] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState("")

  const createMutation = useCreateConversation()
  const uploadMutation = useUploadConversations()

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selectedFile = e.target.files?.[0]
      if (selectedFile) {
        if (!selectedFile.name.endsWith(".json")) {
          setError("Please select a JSON file")
          return
        }
        setFile(selectedFile)
        setError("")
      }
    },
    []
  )

  const handleSubmit = async () => {
    setError("")

    if (mode === "single") {
      if (!category) {
        setError("Please select a category")
        return
      }
      if (!messages.trim()) {
        setError("Please enter conversation messages")
        return
      }

      try {
        const parsedMessages = JSON.parse(messages)
        await createMutation.mutateAsync({
          category,
          messages: parsedMessages,
        })
        setOpen(false)
        resetForm()
      } catch (err) {
        if (err instanceof SyntaxError) {
          setError("Invalid JSON format for messages")
        } else {
          setError("Failed to create conversation")
        }
      }
    } else {
      if (!file) {
        setError("Please select a file")
        return
      }

      try {
        const content = await file.text()
        const data = JSON.parse(content)
        const conversations = Array.isArray(data) ? data : data.conversations

        if (!Array.isArray(conversations)) {
          setError("File must contain an array of conversations")
          return
        }

        const result = await uploadMutation.mutateAsync(conversations)
        if (result.failed > 0) {
          setError(`${result.created} created, ${result.failed} failed`)
        } else {
          setOpen(false)
          resetForm()
        }
      } catch (err) {
        if (err instanceof SyntaxError) {
          setError("Invalid JSON file")
        } else {
          setError("Failed to upload conversations")
        }
      }
    }
  }

  const resetForm = () => {
    setCategory("")
    setMessages("")
    setFile(null)
    setError("")
  }

  const isLoading = createMutation.isPending || uploadMutation.isPending

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Upload Conversation</DialogTitle>
          <DialogDescription>
            Add a single conversation or upload a batch from a JSON file.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          <div className="flex gap-2">
            <Button
              variant={mode === "single" ? "default" : "outline"}
              onClick={() => setMode("single")}
              className="flex-1"
            >
              Single
            </Button>
            <Button
              variant={mode === "batch" ? "default" : "outline"}
              onClick={() => setMode("batch")}
              className="flex-1"
            >
              Batch Upload
            </Button>
          </div>

          {mode === "single" ? (
            <>
              <div className="grid gap-2">
                <Label htmlFor="category">Category</Label>
                <Select value={category} onValueChange={setCategory}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select category" />
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

              <div className="grid gap-2">
                <Label htmlFor="messages">Messages (JSON array)</Label>
                <textarea
                  id="messages"
                  className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 font-mono"
                  placeholder='[{"role": "customer", "content": "..."}, {"role": "agent", "content": "..."}]'
                  value={messages}
                  onChange={(e) => setMessages(e.target.value)}
                />
              </div>
            </>
          ) : (
            <div className="grid gap-2">
              <Label>JSON File</Label>
              <div className="flex items-center justify-center w-full">
                <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer bg-muted/50 hover:bg-muted">
                  <div className="flex flex-col items-center justify-center pt-5 pb-6">
                    {file ? (
                      <>
                        <FileJson className="w-8 h-8 mb-2 text-primary" />
                        <p className="text-sm text-foreground">{file.name}</p>
                      </>
                    ) : (
                      <>
                        <Upload className="w-8 h-8 mb-2 text-muted-foreground" />
                        <p className="text-sm text-muted-foreground">
                          Click to upload JSON file
                        </p>
                      </>
                    )}
                  </div>
                  <Input
                    type="file"
                    accept=".json"
                    className="hidden"
                    onChange={handleFileChange}
                  />
                </label>
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 text-sm text-destructive">
              <AlertCircle className="h-4 w-4" />
              {error}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isLoading}>
            {isLoading ? "Uploading..." : "Upload"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
