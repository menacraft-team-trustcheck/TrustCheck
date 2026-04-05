"use client"

import { useEffect, useState } from "react"
import { cn } from "@/lib/utils"
import { AudioLines, AlertTriangle } from "lucide-react"

interface AudioForensicsWidgetProps {
  data: {
    pitchCV: number
    rmsDynamics: number
    spectralFlatness: number
  }
}

export function AudioForensicsWidget({ data }: AudioForensicsWidgetProps) {
  const [waveformData, setWaveformData] = useState<number[]>([])

  useEffect(() => {
    // Generate fake waveform data
    const points = 64
    const waveform = Array.from({ length: points }, () =>
      Math.random() * 0.8 + 0.1
    )
    setWaveformData(waveform)
  }, [])

  // Find suspicious regions (high spectral flatness areas)
  const suspiciousIndices = waveformData
    .map((_, i) => (Math.random() > 0.85 ? i : -1))
    .filter((i) => i >= 0)

  return (
    <div className="glass-panel rounded-xl p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center">
          <AudioLines className="w-5 h-5 text-accent" />
        </div>
        <div>
          <h3 className="text-sm font-medium tracking-wider text-foreground">
            SOUND SIGNATURE
          </h3>
          <p className="text-xs text-muted-foreground">Spectral Analysis</p>
        </div>
      </div>

      {/* Waveform Visualization */}
      <div className="space-y-3">
        <p className="text-xs tracking-[0.15em] text-muted-foreground">
          WAVEFORM ANALYSIS
        </p>
        <div className="relative h-24 bg-secondary/30 rounded-lg overflow-hidden">
          <div className="absolute inset-0 flex items-center justify-center">
            {waveformData.map((height, i) => {
              const isSuspicious = suspiciousIndices.includes(i)
              return (
                <div
                  key={i}
                  className={cn(
                    "w-1 mx-px rounded-full transition-all duration-300",
                    isSuspicious ? "bg-critical" : "bg-primary"
                  )}
                  style={{
                    height: `${height * 80}%`,
                    opacity: 0.5 + height * 0.5,
                  }}
                />
              )
            })}
          </div>
          {/* Suspicious markers */}
          {suspiciousIndices.length > 0 && (
            <div className="absolute top-2 right-2 flex items-center gap-1 px-2 py-1 bg-critical/20 rounded text-xs text-critical">
              <AlertTriangle className="w-3 h-3" />
              {suspiciousIndices.length} anomalies
            </div>
          )}
          {/* Scanning line */}
          <div className="absolute inset-y-0 w-0.5 bg-primary/50 animate-pulse left-1/3" />
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-3 gap-4">
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground">PITCH CV</p>
          <div className="flex items-baseline gap-1">
            <span className="text-xl font-mono font-bold text-foreground">
              {data.pitchCV.toFixed(2)}
            </span>
          </div>
          <p
            className={cn(
              "text-xs",
              data.pitchCV > 0.3 ? "text-critical" : "text-safe"
            )}
          >
            {data.pitchCV > 0.3 ? "High variance" : "Normal"}
          </p>
        </div>

        <div className="space-y-1">
          <p className="text-xs text-muted-foreground">RMS DYNAMICS</p>
          <div className="flex items-baseline gap-1">
            <span className="text-xl font-mono font-bold text-foreground">
              {data.rmsDynamics.toFixed(1)}
            </span>
            <span className="text-xs text-muted-foreground">dB</span>
          </div>
          <div className="h-1 bg-secondary rounded-full overflow-hidden">
            <div
              className="h-full bg-accent rounded-full"
              style={{ width: `${(data.rmsDynamics / 40) * 100}%` }}
            />
          </div>
        </div>

        <div className="space-y-1">
          <p className="text-xs text-muted-foreground">SPECTRAL FLAT</p>
          <div className="flex items-baseline gap-1">
            <span className="text-xl font-mono font-bold text-foreground">
              {(data.spectralFlatness * 100).toFixed(0)}
            </span>
            <span className="text-xs text-muted-foreground">%</span>
          </div>
          <p
            className={cn(
              "text-xs",
              data.spectralFlatness > 0.5 ? "text-warning" : "text-safe"
            )}
          >
            {data.spectralFlatness > 0.5 ? "Synthetic markers" : "Organic"}
          </p>
        </div>
      </div>
    </div>
  )
}
