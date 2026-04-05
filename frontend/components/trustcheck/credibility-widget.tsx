"use client"

import { cn } from "@/lib/utils"
import { Globe, AlertTriangle, Zap, ShieldCheck, ShieldX } from "lucide-react"

interface CredibilityWidgetProps {
  data: {
    domainScore: number
    emotionalAmplification: number
    sourceVerified: boolean
  }
}

export function CredibilityWidget({ data }: CredibilityWidgetProps) {
  return (
    <div className="glass-panel rounded-xl p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-chart-4/10 flex items-center justify-center">
          <Globe className="w-5 h-5 text-chart-4" />
        </div>
        <div>
          <h3 className="text-sm font-medium tracking-wider text-foreground">
            CREDIBILITY AXIS
          </h3>
          <p className="text-xs text-muted-foreground">Source & Context Analysis</p>
        </div>
      </div>

      {/* Domain Reputation Meter */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-xs tracking-[0.15em] text-muted-foreground">
            DOMAIN REPUTATION
          </p>
          <span
            className={cn(
              "text-sm font-mono font-bold",
              data.domainScore > 60
                ? "text-safe"
                : data.domainScore > 30
                ? "text-warning"
                : "text-critical"
            )}
          >
            {data.domainScore}/100
          </span>
        </div>
        <div className="relative h-3 bg-secondary rounded-full overflow-hidden">
          {/* Gradient bar */}
          <div
            className="absolute inset-y-0 left-0 rounded-full transition-all duration-1000"
            style={{
              width: `${data.domainScore}%`,
              background: `linear-gradient(90deg, 
                oklch(0.60 0.25 25) 0%, 
                oklch(0.75 0.18 85) 50%, 
                oklch(0.70 0.20 145) 100%
              )`,
            }}
          />
          {/* Marker lines */}
          <div className="absolute inset-0 flex justify-between px-1">
            {[0, 25, 50, 75, 100].map((mark) => (
              <div
                key={mark}
                className="w-px h-full bg-glass-border"
                style={{ left: `${mark}%` }}
              />
            ))}
          </div>
        </div>
        <div className="flex justify-between text-[10px] text-muted-foreground">
          <span>Untrusted</span>
          <span>Verified</span>
        </div>
      </div>

      {/* Emotional Amplification Warning */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-xs tracking-[0.15em] text-muted-foreground flex items-center gap-2">
            <Zap className="w-3.5 h-3.5" />
            EMOTIONAL AMPLIFICATION
          </p>
          <span
            className={cn(
              "text-sm font-mono font-bold",
              data.emotionalAmplification > 60
                ? "text-critical"
                : data.emotionalAmplification > 40
                ? "text-warning"
                : "text-safe"
            )}
          >
            {data.emotionalAmplification}%
          </span>
        </div>
        <div className="h-2 bg-secondary rounded-full overflow-hidden">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-1000",
              data.emotionalAmplification > 60
                ? "bg-critical"
                : data.emotionalAmplification > 40
                ? "bg-warning"
                : "bg-safe"
            )}
            style={{ width: `${data.emotionalAmplification}%` }}
          />
        </div>
        {data.emotionalAmplification > 50 && (
          <div className="flex items-center gap-2 p-2 bg-warning/10 rounded-lg">
            <AlertTriangle className="w-4 h-4 text-warning flex-shrink-0" />
            <p className="text-xs text-warning">
              High emotional language detected. Content may be designed to provoke
              strong reactions.
            </p>
          </div>
        )}
      </div>

      {/* Source Verification Badge */}
      <div className="pt-4 border-t border-glass-border">
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">Source Verification</span>
          <div
            className={cn(
              "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium",
              data.sourceVerified
                ? "bg-safe/10 text-safe"
                : "bg-critical/10 text-critical"
            )}
          >
            {data.sourceVerified ? (
              <>
                <ShieldCheck className="w-4 h-4" />
                VERIFIED
              </>
            ) : (
              <>
                <ShieldX className="w-4 h-4" />
                UNVERIFIED
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
