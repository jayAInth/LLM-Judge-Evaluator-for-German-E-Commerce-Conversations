import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(date: string | Date | null | undefined): string {
  if (!date) return "-"
  try {
    const d = new Date(date)
    if (isNaN(d.getTime())) return "-"
    return new Intl.DateTimeFormat("de-DE", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(d)
  } catch {
    return "-"
  }
}

export function formatScore(score: number | null | undefined): string {
  if (score == null) return "-"
  return score.toFixed(2)
}

export function getScoreColor(score: number | null | undefined): string {
  const s = score ?? 0
  if (s >= 8) return "text-green-500"
  if (s >= 6) return "text-yellow-500"
  if (s >= 4) return "text-orange-500"
  return "text-red-500"
}

export function getScoreBgColor(score: number | null | undefined): string {
  const s = score ?? 0
  if (s >= 8) return "bg-green-500/10"
  if (s >= 6) return "bg-yellow-500/10"
  if (s >= 4) return "bg-orange-500/10"
  return "bg-red-500/10"
}

export function getCategoryLabel(category: string): string {
  const labels: Record<string, string> = {
    retoure: "Retoure",
    beschwerde: "Beschwerde",
    produktanfrage: "Produktanfrage",
    lieferung: "Lieferung",
    zahlung: "Zahlung",
    konto: "Konto",
    allgemein: "Allgemein",
  }
  return labels[category] || category
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    PENDING: "bg-yellow-500/10 text-yellow-500",
    RUNNING: "bg-blue-500/10 text-blue-500",
    COMPLETED: "bg-green-500/10 text-green-500",
    FAILED: "bg-red-500/10 text-red-500",
    CANCELLED: "bg-gray-500/10 text-gray-500",
  }
  return colors[status] || "bg-gray-500/10 text-gray-500"
}
