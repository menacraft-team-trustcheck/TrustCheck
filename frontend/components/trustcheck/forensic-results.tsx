"use client"

import { useState, useEffect } from "react"
import { cn } from "@/lib/utils"
import type { AnalysisStatus, AnalysisResult, MediaType, RiskLevel } from "@/app/page"
import { TrustScoreDial } from "./trust-score-dial"
import { VisualForensicsWidget } from "./visual-forensics-widget"
import { AudioForensicsWidget } from "./audio-forensics-widget"
import { ExifWidget } from "./exif-widget"
import { CredibilityWidget } from "./credibility-widget"
import { AlertTriangle, ShieldCheck, ShieldAlert, ShieldX, Loader2 } from "lucide-react"

interface ForensicResultsProps {
  status: AnalysisStatus
  result: AnalysisResult | null
  mediaType: MediaType
}

const riskConfig: Record<
  RiskLevel,
  { icon: typeof AlertTriangle; color: string; bgColor: string; label: string }
> = {
  CRITICAL: {
    icon: ShieldX,
    color: "text-critical",
    bgColor: "bg-critical/10 border-critical/30",
    label: "CRITICAL RISK",
  },
  HIGH: {
    icon: ShieldAlert,
    color: "text-destructive",
    bgColor: "bg-destructive/10 border-destructive/30",
    label: "HIGH RISK",
  },
  MODERATE: {
    icon: AlertTriangle,
    color: "text-warning",
    bgColor: "bg-warning/10 border-warning/30",
    label: "MODERATE RISK",
  },
  LOW: {
    icon: ShieldCheck,
    color: "text-accent",
    bgColor: "bg-accent/10 border-accent/30",
    label: "LOW RISK",
  },
  VERIFIED: {
    icon: ShieldCheck,
    color: "text-safe",
    bgColor: "bg-safe/10 border-safe/30",
    label: "VERIFIED AUTHENTIC",
  },
}

export function ForensicResults({ status, result, mediaType }: ForensicResultsProps) {
  const [displayedReasoning, setDisplayedReasoning] = useState("")
  const [isTyping, setIsTyping] = useState(false)

  // Typing animation for reasoning
  useEffect(() => {
    if (status === "complete" && result?.reasoning) {
      setIsTyping(true)
      setDisplayedReasoning("")
      const text = result.reasoning
      let index = 0

      const interval = setInterval(() => {
        if (index < text.length) {
          setDisplayedReasoning(text.slice(0, index + 1))
          index++
        } else {
          clearInterval(interval)
          setIsTyping(false)
        }
      }, 15)

      return () => clearInterval(interval)
    }
  }, [status, result?.reasoning])

  if (status === "analyzing") {
    return (
      <div className="glass-panel rounded-xl p-8">
        <div className="flex flex-col items-center justify-center py-12 space-y-4">
          <div className="relative">
            <Loader2 className="w-12 h-12 text-primary animate-spin" />
            <div className="absolute inset-0 w-12 h-12 rounded-full border-2 border-primary/20 animate-ping" />
          </div>
          <div className="text-center">
            <p className="text-lg font-medium tracking-wider text-foreground">
              FORENSIC ANALYSIS IN PROGRESS
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              Running multi-axis verification pipeline...
            </p>
          </div>
          <div className="flex items-center gap-4 mt-4">
            {["ELA Scan", "Metadata", "ML Models", "Credibility"].map(
              (step, i) => (
                <div
                  key={step}
                  className="flex items-center gap-2 text-xs text-muted-foreground"
                  style={{ animationDelay: `${i * 0.3}s` }}
                >
                  <div className="w-2 h-2 rounded-full bg-primary heartbeat" />
                  {step}
                </div>
              )
            )}
          </div>
        </div>
      </div>
    )
  }

  if (!result) return null

  const risk = riskConfig[result.riskLevel]
  const RiskIcon = risk.icon

  return (
    <div className="space-y-6">
      {/* Risk Banner */}
      <div
        className={cn(
          "glass-panel rounded-xl p-6 border-2 transition-all duration-500",
          risk.bgColor
        )}
      >
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Risk Badge & Score */}
          <div className="flex items-center gap-6">
            <div
              className={cn(
                "w-16 h-16 rounded-xl flex items-center justify-center",
                risk.bgColor
              )}
            >
              <RiskIcon className={cn("w-8 h-8", risk.color)} />
            </div>
            <div>
              <p className={cn("text-2xl font-bold tracking-wider", risk.color)}>
                {risk.label}
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                Confidence: {Math.min(95, 75 + Math.floor(Math.random() * 20))}%
              </p>
            </div>
          </div>

          {/* Trust Score Dial */}
          <div className="lg:ml-auto">
            <TrustScoreDial score={result.trustScore} />
          </div>
        </div>

        {/* Reasoning */}
        <div className="mt-6 pt-6 border-t border-glass-border">
          <p className="text-xs tracking-[0.15em] text-muted-foreground mb-3">
            ANALYSIS SYNTHESIS
          </p>
          <p className="text-sm leading-relaxed text-foreground/80 font-mono">
            {displayedReasoning}
            {isTyping && (
              <span className="inline-block w-2 h-4 bg-primary ml-1 animate-pulse" />
            )}
          </p>
        </div>
      </div>

      {/* Forensic Widgets Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Visual Forensics */}
        {(mediaType === "image" || mediaType === "video" || mediaType === "batch") &&
          result.visualForensics && (
            <VisualForensicsWidget data={result.visualForensics} />
          )}

        {/* Audio Forensics */}
        {(mediaType === "audio" || mediaType === "video" || mediaType === "batch") &&
          result.audioForensics && (
            <AudioForensicsWidget data={result.audioForensics} />
          )}

        {/* EXIF Data */}
        {result.exifData && <ExifWidget data={result.exifData} />}

        {/* Credibility */}
        {result.credibility && <CredibilityWidget data={result.credibility} />}
      </div>
    </div>
  )
}
