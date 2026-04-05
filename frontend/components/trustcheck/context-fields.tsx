"use client"

import { cn } from "@/lib/utils"
import { FileText, Link2, MapPin } from "lucide-react"

interface ContextFieldsProps {
  claim: string
  setClaim: (value: string) => void
  sourceUrl: string
  setSourceUrl: (value: string) => void
  location: string
  setLocation: (value: string) => void
  disabled?: boolean
}

export function ContextFields({
  claim,
  setClaim,
  sourceUrl,
  setSourceUrl,
  location,
  setLocation,
  disabled,
}: ContextFieldsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {/* Claim Field */}
      <div className="space-y-2">
        <label className="flex items-center gap-2 text-xs tracking-[0.15em] text-muted-foreground">
          <FileText className="w-3.5 h-3.5" />
          CLAIM / DESCRIPTION
        </label>
        <input
          type="text"
          value={claim}
          onChange={(e) => setClaim(e.target.value)}
          disabled={disabled}
          placeholder="What is being claimed about this media?"
          className={cn(
            "w-full px-4 py-3 rounded-lg",
            "bg-secondary/30 border-0 outline-none",
            "text-sm text-foreground placeholder:text-muted-foreground/50",
            "focus:ring-1 focus:ring-primary/50 focus:bg-secondary/50",
            "transition-all duration-200",
            "disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        />
      </div>

      {/* Source URL Field */}
      <div className="space-y-2">
        <label className="flex items-center gap-2 text-xs tracking-[0.15em] text-muted-foreground">
          <Link2 className="w-3.5 h-3.5" />
          SOURCE URL
        </label>
        <input
          type="url"
          value={sourceUrl}
          onChange={(e) => setSourceUrl(e.target.value)}
          disabled={disabled}
          placeholder="https://example.com/source"
          className={cn(
            "w-full px-4 py-3 rounded-lg",
            "bg-secondary/30 border-0 outline-none",
            "text-sm text-foreground placeholder:text-muted-foreground/50 font-mono",
            "focus:ring-1 focus:ring-primary/50 focus:bg-secondary/50",
            "transition-all duration-200",
            "disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        />
      </div>

      {/* Location Field */}
      <div className="space-y-2">
        <label className="flex items-center gap-2 text-xs tracking-[0.15em] text-muted-foreground">
          <MapPin className="w-3.5 h-3.5" />
          CLAIMED LOCATION
        </label>
        <input
          type="text"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          disabled={disabled}
          placeholder="City, Country or Coordinates"
          className={cn(
            "w-full px-4 py-3 rounded-lg",
            "bg-secondary/30 border-0 outline-none",
            "text-sm text-foreground placeholder:text-muted-foreground/50",
            "focus:ring-1 focus:ring-primary/50 focus:bg-secondary/50",
            "transition-all duration-200",
            "disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        />
      </div>
    </div>
  )
}
