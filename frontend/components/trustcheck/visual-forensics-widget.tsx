"use client"

import { cn } from "@/lib/utils"
import { Eye, Grid3X3, AlertCircle } from "lucide-react"

interface VisualForensicsWidgetProps {
  data: {
    elaMax: number
    manipulationRegions: number
    metadataConsistency: number
  }
}

export function VisualForensicsWidget({ data }: VisualForensicsWidgetProps) {
  return (
    <div className="glass-panel rounded-xl p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
          <Eye className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h3 className="text-sm font-medium tracking-wider text-foreground">
            VISUAL FORENSICS
          </h3>
          <p className="text-xs text-muted-foreground">Error Level Analysis</p>
        </div>
      </div>

      {/* ELA Heatmap Visualization */}
      <div className="space-y-3">
        <p className="text-xs tracking-[0.15em] text-muted-foreground">
          ELA HEATMAP SIMULATION
        </p>
        <div className="relative grid grid-cols-8 gap-0.5 rounded-lg overflow-hidden">
          {Array.from({ length: 64 }).map((_, i) => {
            const isManipulated = Math.random() > 0.7 && data.manipulationRegions > 0
            const intensity = isManipulated
              ? Math.random() * 0.8 + 0.2
              : Math.random() * 0.2
            return (
              <div
                key={i}
                className={cn(
                  "aspect-square transition-all duration-300",
                  isManipulated ? "bg-critical" : "bg-secondary"
                )}
                style={{
                  opacity: 0.3 + intensity * 0.7,
                }}
              />
            )
          })}
          {/* Overlay grid lines */}
          <div className="absolute inset-0 pointer-events-none">
            <div className="w-full h-full grid grid-cols-8 gap-0.5">
              {Array.from({ length: 64 }).map((_, i) => (
                <div key={i} className="border border-glass-border/30" />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-3 gap-4">
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground">ELA MAX</p>
          <div className="flex items-baseline gap-1">
            <span className="text-xl font-mono font-bold text-foreground">
              {data.elaMax}
            </span>
            <span className="text-xs text-muted-foreground">%</span>
          </div>
          <div className="h-1 bg-secondary rounded-full overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-1000",
                data.elaMax > 60 ? "bg-critical" : data.elaMax > 30 ? "bg-warning" : "bg-safe"
              )}
              style={{ width: `${data.elaMax}%` }}
            />
          </div>
        </div>

        <div className="space-y-1">
          <p className="text-xs text-muted-foreground flex items-center gap-1">
            <Grid3X3 className="w-3 h-3" />
            REGIONS
          </p>
          <div className="flex items-baseline gap-1">
            <span className="text-xl font-mono font-bold text-foreground">
              {data.manipulationRegions}
            </span>
            <span className="text-xs text-muted-foreground">found</span>
          </div>
          <div className="flex items-center gap-1">
            {Array.from({ length: 5 }).map((_, i) => (
              <div
                key={i}
                className={cn(
                  "w-3 h-3 rounded-sm",
                  i < data.manipulationRegions ? "bg-critical" : "bg-secondary"
                )}
              />
            ))}
          </div>
        </div>

        <div className="space-y-1">
          <p className="text-xs text-muted-foreground flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            META
          </p>
          <div className="flex items-baseline gap-1">
            <span className="text-xl font-mono font-bold text-foreground">
              {data.metadataConsistency}
            </span>
            <span className="text-xs text-muted-foreground">%</span>
          </div>
          <div className="h-1 bg-secondary rounded-full overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-1000",
                data.metadataConsistency > 70 ? "bg-safe" : data.metadataConsistency > 40 ? "bg-warning" : "bg-critical"
              )}
              style={{ width: `${data.metadataConsistency}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
