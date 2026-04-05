"use client"

import { useEffect, useState } from "react"
import { cn } from "@/lib/utils"

interface TrustScoreDialProps {
  score: number
}

export function TrustScoreDial({ score }: TrustScoreDialProps) {
  const [animatedScore, setAnimatedScore] = useState(0)

  useEffect(() => {
    const duration = 1500
    const startTime = Date.now()

    const animate = () => {
      const elapsed = Date.now() - startTime
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3) // Ease out cubic
      setAnimatedScore(Math.floor(eased * score))

      if (progress < 1) {
        requestAnimationFrame(animate)
      }
    }

    requestAnimationFrame(animate)
  }, [score])

  const getScoreColor = (s: number) => {
    if (s >= 70) return { stroke: "stroke-safe", text: "text-safe", glow: "neon-glow-emerald" }
    if (s >= 50) return { stroke: "stroke-accent", text: "text-accent", glow: "neon-glow-emerald" }
    if (s >= 30) return { stroke: "stroke-warning", text: "text-warning", glow: "" }
    return { stroke: "stroke-critical", text: "text-critical", glow: "" }
  }

  const colors = getScoreColor(score)
  const circumference = 2 * Math.PI * 45
  const strokeDashoffset = circumference - (animatedScore / 100) * circumference

  return (
    <div className={cn("relative w-32 h-32", colors.glow)}>
      <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
        {/* Background circle */}
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          strokeWidth="8"
          className="stroke-secondary/50"
        />
        {/* Progress circle */}
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          strokeWidth="8"
          strokeLinecap="round"
          className={cn("transition-all duration-1000", colors.stroke)}
          style={{
            strokeDasharray: circumference,
            strokeDashoffset,
          }}
        />
        {/* Tick marks */}
        {Array.from({ length: 20 }).map((_, i) => {
          const angle = (i / 20) * 360
          const isHighlighted = (i / 20) * 100 <= animatedScore
          return (
            <line
              key={i}
              x1="50"
              y1="8"
              x2="50"
              y2="12"
              className={cn(
                "transition-all duration-300",
                isHighlighted ? colors.stroke : "stroke-secondary/30"
              )}
              strokeWidth="1"
              transform={`rotate(${angle} 50 50)`}
            />
          )
        })}
      </svg>
      {/* Center text */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={cn("text-3xl font-bold font-mono", colors.text)}>
          {animatedScore}
        </span>
        <span className="text-[10px] tracking-[0.2em] text-muted-foreground">
          TRUST %
        </span>
      </div>
    </div>
  )
}
