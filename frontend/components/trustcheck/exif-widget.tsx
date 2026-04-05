"use client"

import { cn } from "@/lib/utils"
import { Camera, AlertTriangle, CheckCircle2 } from "lucide-react"

interface ExifWidgetProps {
  data: {
    camera: string
    focalLength: string
    iso: string
    flash: string
    gps: string
    timestamp: string
  }
}

const exifFields = [
  { key: "camera", label: "Camera/Device" },
  { key: "focalLength", label: "Focal Length" },
  { key: "iso", label: "ISO Speed" },
  { key: "flash", label: "Flash" },
  { key: "gps", label: "GPS Coordinates" },
  { key: "timestamp", label: "Timestamp" },
] as const

export function ExifWidget({ data }: ExifWidgetProps) {
  const getFieldStatus = (value: string) => {
    const suspicious = [
      "Unknown",
      "Stripped",
      "Not Available",
      "Inconsistent",
      "N/A",
    ]
    return suspicious.some((s) => value.includes(s)) ? "warning" : "ok"
  }

  const warningCount = Object.values(data).filter(
    (v) => getFieldStatus(v) === "warning"
  ).length

  return (
    <div className="glass-panel rounded-xl p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-chart-3/10 flex items-center justify-center">
            <Camera className="w-5 h-5 text-chart-3" />
          </div>
          <div>
            <h3 className="text-sm font-medium tracking-wider text-foreground">
              EXIF PROFILING
            </h3>
            <p className="text-xs text-muted-foreground">Hardware Metadata</p>
          </div>
        </div>
        {warningCount > 0 && (
          <div className="flex items-center gap-1 px-2 py-1 bg-warning/10 rounded text-xs text-warning">
            <AlertTriangle className="w-3 h-3" />
            {warningCount} issues
          </div>
        )}
      </div>

      {/* Data Table */}
      <div className="space-y-1">
        {exifFields.map((field) => {
          const value = data[field.key]
          const status = getFieldStatus(value)
          return (
            <div
              key={field.key}
              className={cn(
                "flex items-center justify-between py-2 px-3 rounded-lg",
                "transition-all duration-200 hover:bg-secondary/30"
              )}
            >
              <span className="text-xs text-muted-foreground tracking-wide">
                {field.label}
              </span>
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "text-sm font-mono",
                    status === "warning"
                      ? "text-warning"
                      : "text-foreground"
                  )}
                >
                  {value}
                </span>
                {status === "warning" ? (
                  <AlertTriangle className="w-3.5 h-3.5 text-warning" />
                ) : (
                  <CheckCircle2 className="w-3.5 h-3.5 text-safe" />
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Summary Bar */}
      <div className="pt-4 border-t border-glass-border">
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">Metadata Integrity</span>
          <span
            className={cn(
              "font-medium",
              warningCount > 3
                ? "text-critical"
                : warningCount > 1
                ? "text-warning"
                : "text-safe"
            )}
          >
            {warningCount > 3
              ? "COMPROMISED"
              : warningCount > 1
              ? "PARTIAL"
              : "INTACT"}
          </span>
        </div>
        <div className="mt-2 h-1.5 bg-secondary rounded-full overflow-hidden flex">
          {exifFields.map((field, i) => {
            const status = getFieldStatus(data[field.key])
            return (
              <div
                key={i}
                className={cn(
                  "flex-1 h-full",
                  status === "warning" ? "bg-warning" : "bg-safe",
                  i > 0 && "ml-0.5"
                )}
              />
            )
          })}
        </div>
      </div>
    </div>
  )
}
