import { useState } from "react"
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
import { useCreateJob } from "@/hooks/useJobs"

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

interface CreateJobDialogProps {
  children: React.ReactNode
}

export function CreateJobDialog({ children }: CreateJobDialogProps) {
  const [open, setOpen] = useState(false)
  const [category, setCategory] = useState("all")
  const [dateFrom, setDateFrom] = useState("")
  const [dateTo, setDateTo] = useState("")

  const createMutation = useCreateJob()

  const handleSubmit = async () => {
    await createMutation.mutateAsync({
      category_filter: category !== "all" ? category : undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    })
    setOpen(false)
    resetForm()
  }

  const resetForm = () => {
    setCategory("all")
    setDateFrom("")
    setDateTo("")
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Create Batch Job</DialogTitle>
          <DialogDescription>
            Create a new batch evaluation job with filters.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label>Category Filter</Label>
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

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label>Date From</Label>
              <Input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label>Date To</Label>
              <Input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
              />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={createMutation.isPending}>
            {createMutation.isPending ? "Creating..." : "Create Job"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
