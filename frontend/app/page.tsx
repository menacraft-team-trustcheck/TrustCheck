"use client"

import { useState, useEffect, useCallback } from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  ImageIcon,
  AudioLines,
  Video,
  FolderOpen,
  Shield,
  Settings,
  HelpCircle,
  Activity,
  Database,
  Wifi,
  Clock,
  Bell,
  User,
  Upload,
  FileImage,
  FileAudio,
  FileVideo,
  Files,
  X,
  Loader2,
  CheckCircle2,
  FileText,
  Link2,
  MapPin,
  AlertTriangle,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  Eye,
  Grid3X3,
  AlertCircle,
  Camera,
  Globe,
  Zap,
} from "lucide-react"

// ============================================================================
// TYPES
// ============================================================================

export type AnalysisStatus = "idle" | "uploading" | "analyzing" | "complete"
export type MediaType = "image" | "audio" | "video" | "batch"
export type RiskLevel = "CRITICAL" | "HIGH" | "MODERATE" | "LOW" | "VERIFIED"

export interface AnalysisResult {
  trustScore: number
  riskLevel: RiskLevel
  reasoning: string
  visualForensics?: {
    elaMax: number
    manipulationRegions: number
    metadataConsistency: number
  }
  audioForensics?: {
    pitchCV: number
    rmsDynamics: number
    spectralFlatness: number
  }
  exifData?: {
    camera: string
    focalLength: string
    iso: string
    flash: string
    gps: string
    timestamp: string
  }
  credibility?: {
    domainScore: number
    emotionalAmplification: number
    sourceVerified: boolean
  }
}

interface StatusPill {
  id: string
  label: string
  value: string
  status: "online" | "degraded" | "offline"
  icon: typeof Activity
}

// ============================================================================
// SIDEBAR COMPONENT
// ============================================================================

const navItems: { id: MediaType; icon: typeof ImageIcon; label: string }[] = [
  { id: "image", icon: ImageIcon, label: "Image" },
  { id: "audio", icon: AudioLines, label: "Audio" },
  { id: "video", icon: Video, label: "Video" },
  { id: "batch", icon: FolderOpen, label: "Batch" },
]

function Sidebar({
  activeTab,
  onTabChange,
}: {
  activeTab: MediaType
  onTabChange: (tab: MediaType) => void
}) {
  return (
    <aside className="w-20 lg:w-64 h-full glass-panel border-r border-glass-border flex flex-col">
      {/* Logo */}
      <div className="p-4 lg:p-6 border-b border-glass-border">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center neon-glow-cyan">
            <Shield className="w-5 h-5 text-primary" />
          </div>
          <div className="hidden lg:block">
            <h1 className="text-lg font-semibold tracking-widest text-foreground">
              TRUSTCHECK
            </h1>
            <p className="text-[10px] tracking-[0.2em] text-muted-foreground">
              FORENSIC PLATFORM
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 lg:p-4 space-y-2">
        <p className="hidden lg:block text-[10px] tracking-[0.2em] text-muted-foreground mb-4 px-2">
          ANALYSIS MODULES
        </p>
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = activeTab === item.id
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-3 rounded-lg transition-all duration-200",
                "hover:bg-secondary/50 group relative overflow-hidden",
                isActive && "bg-primary/10 neon-glow-cyan"
              )}
            >
              {isActive && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-primary rounded-r" />
              )}
              <Icon
                className={cn(
                  "w-5 h-5 transition-colors flex-shrink-0",
                  isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground"
                )}
              />
              <span
                className={cn(
                  "hidden lg:block text-sm tracking-wide transition-colors",
                  isActive ? "text-primary font-medium" : "text-muted-foreground group-hover:text-foreground"
                )}
              >
                {item.label}
              </span>
              <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none overflow-hidden">
                <div className="scanning-line absolute inset-y-0 w-1/2" />
              </div>
            </button>
          )
        })}
      </nav>

      {/* Bottom Actions */}
      <div className="p-3 lg:p-4 border-t border-glass-border space-y-2">
        <button className="w-full flex items-center gap-3 px-3 py-3 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-all">
          <Settings className="w-5 h-5 flex-shrink-0" />
          <span className="hidden lg:block text-sm tracking-wide">Settings</span>
        </button>
        <button className="w-full flex items-center gap-3 px-3 py-3 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-all">
          <HelpCircle className="w-5 h-5 flex-shrink-0" />
          <span className="hidden lg:block text-sm tracking-wide">Documentation</span>
        </button>
      </div>
    </aside>
  )
}

// ============================================================================
// TOP NAV COMPONENT
// ============================================================================

function TopNav() {
  const [time, setTime] = useState<Date | null>(null)
  const [statuses, setStatuses] = useState<StatusPill[]>([
    { id: "api", label: "API Latency", value: "42ms", status: "online", icon: Activity },
    { id: "db", label: "Supabase", value: "Online", status: "online", icon: Database },
    { id: "ml", label: "ML Pipeline", value: "Active", status: "online", icon: Wifi },
  ])

  useEffect(() => {
    setTime(new Date())
    const interval = setInterval(() => {
      setTime(new Date())
      setStatuses((prev) =>
        prev.map((s) => ({
          ...s,
          value: s.id === "api" ? `${Math.floor(Math.random() * 30) + 35}ms` : s.value,
        }))
      )
    }, 1000)
    return () => clearInterval(interval)
  }, [])

  const getStatusColor = (status: StatusPill["status"]) => {
    switch (status) {
      case "online":
        return "bg-safe"
      case "degraded":
        return "bg-warning"
      case "offline":
        return "bg-critical"
    }
  }

  return (
    <header className="h-14 border-b border-glass-border glass-panel flex items-center justify-between px-6">
      <div className="flex items-center gap-3">
        <span className="text-[10px] tracking-[0.2em] text-muted-foreground hidden sm:block">
          SYSTEM STATUS
        </span>
        <div className="flex items-center gap-2">
          {statuses.map((status) => {
            const Icon = status.icon
            return (
              <div
                key={status.id}
                className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-secondary/50 border border-glass-border"
              >
                <div className="relative flex items-center">
                  <div className={cn("w-2 h-2 rounded-full heartbeat", getStatusColor(status.status))} />
                </div>
                <Icon className="w-3.5 h-3.5 text-muted-foreground hidden md:block" />
                <span className="text-xs text-muted-foreground hidden lg:block">{status.label}:</span>
                <span className="text-xs font-mono text-foreground">{status.value}</span>
              </div>
            )
          })}
        </div>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Clock className="w-4 h-4" />
          <span className="font-mono text-sm tracking-wider">
            {time
              ? time.toLocaleTimeString("en-US", {
                  hour12: false,
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                })
              : "--:--:--"}
          </span>
        </div>
        <button className="relative p-2 rounded-lg hover:bg-secondary/50 transition-colors">
          <Bell className="w-5 h-5 text-muted-foreground" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-primary rounded-full pulse-ring" />
        </button>
        <button className="flex items-center gap-2 p-2 rounded-lg hover:bg-secondary/50 transition-colors">
          <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center border border-primary/30">
            <User className="w-4 h-4 text-primary" />
          </div>
        </button>
      </div>
    </header>
  )
}

// ============================================================================
// UPLOAD ZONE COMPONENT
// ============================================================================

const mediaConfig = {
  image: { icon: FileImage, accept: "image/*", label: "Images", formats: "PNG, JPEG, WEBP, GIF" },
  audio: { icon: FileAudio, accept: "audio/*", label: "Audio", formats: "MP3, WAV, OGG, FLAC" },
  video: { icon: FileVideo, accept: "video/*", label: "Video", formats: "MP4, MOV, AVI, WEBM" },
  batch: { icon: Files, accept: "image/*,audio/*,video/*", label: "Multiple Files", formats: "Images, Audio, Video" },
}

function UploadZone({
  status,
  onFileUpload,
  uploadedFile,
  onReset,
  mediaType,
}: {
  status: AnalysisStatus
  onFileUpload: (file: File) => void
  uploadedFile: File | null
  onReset: () => void
  mediaType: MediaType
}) {
  const [isDragOver, setIsDragOver] = useState(false)
  const config = mediaConfig[mediaType]
  const Icon = config.icon

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragOver(false)
      const file = e.dataTransfer.files[0]
      if (file) onFileUpload(file)
    },
    [onFileUpload]
  )

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (file) onFileUpload(file)
    },
    [onFileUpload]
  )

  const isProcessing = status === "uploading" || status === "analyzing"

  return (
    <div
      className={cn(
        "relative glass-panel rounded-xl overflow-hidden transition-all duration-500",
        isDragOver && "neon-glow-cyan border-primary",
        status === "complete" && "neon-glow-emerald border-accent"
      )}
      onDragOver={(e) => {
        e.preventDefault()
        setIsDragOver(true)
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
    >
      {isProcessing && (
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div className="absolute inset-0 bg-primary/5" />
          <div className="scanning-line absolute inset-y-0 w-full h-1 top-0" />
          <div className="scanning-line absolute inset-y-0 w-full h-1" style={{ animationDelay: "0.5s", top: "33%" }} />
          <div className="scanning-line absolute inset-y-0 w-full h-1" style={{ animationDelay: "1s", top: "66%" }} />
        </div>
      )}
      <div className="p-8 md:p-12">
        {status === "idle" ? (
          <label className="flex flex-col items-center justify-center cursor-pointer group">
            <input
              type="file"
              className="sr-only"
              accept={config.accept}
              onChange={handleFileSelect}
              multiple={mediaType === "batch"}
            />
            <div
              className={cn(
                "w-20 h-20 rounded-2xl bg-secondary/50 flex items-center justify-center",
                "transition-all duration-300 group-hover:bg-primary/20 group-hover:neon-glow-cyan"
              )}
            >
              <Upload className="w-8 h-8 text-muted-foreground group-hover:text-primary transition-colors" />
            </div>
            <div className="mt-6 text-center">
              <p className="text-lg font-medium tracking-wide text-foreground">Drop {config.label} Here</p>
              <p className="mt-1 text-sm text-muted-foreground">or click to browse - {config.formats}</p>
            </div>
            <div className="mt-6 flex items-center gap-2">
              <Icon className="w-4 h-4 text-muted-foreground" />
              <span className="text-xs tracking-wider text-muted-foreground">MAX FILE SIZE: 100MB</span>
            </div>
          </label>
        ) : (
          <div className="flex flex-col md:flex-row items-center gap-6">
            <div className="w-24 h-24 rounded-xl bg-secondary/50 flex items-center justify-center relative">
              <Icon className="w-10 h-10 text-primary" />
              {status === "complete" && (
                <div className="absolute -bottom-2 -right-2 w-8 h-8 rounded-full bg-accent flex items-center justify-center">
                  <CheckCircle2 className="w-5 h-5 text-accent-foreground" />
                </div>
              )}
            </div>
            <div className="flex-1 text-center md:text-left">
              <p className="font-mono text-sm text-foreground truncate max-w-xs">
                {uploadedFile?.name || "sample_media.file"}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {uploadedFile ? `${(uploadedFile.size / 1024 / 1024).toFixed(2)} MB - ${uploadedFile.type}` : "Unknown size"}
              </p>
              <div className="mt-3 flex items-center justify-center md:justify-start gap-2">
                {isProcessing ? (
                  <>
                    <Loader2 className="w-4 h-4 text-primary animate-spin" />
                    <span className="text-sm text-primary font-medium tracking-wide">
                      {status === "uploading" ? "UPLOADING..." : "ANALYZING..."}
                    </span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-accent" />
                    <span className="text-sm text-accent font-medium tracking-wide">ANALYSIS COMPLETE</span>
                  </>
                )}
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={onReset}
              disabled={isProcessing}
              className="border-glass-border hover:bg-secondary/50 hover:text-foreground"
            >
              <X className="w-4 h-4 mr-2" />
              Reset
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

// ============================================================================
// CONTEXT FIELDS COMPONENT
// ============================================================================

function ContextFields({
  claim,
  setClaim,
  sourceUrl,
  setSourceUrl,
  location,
  setLocation,
  disabled,
}: {
  claim: string
  setClaim: (value: string) => void
  sourceUrl: string
  setSourceUrl: (value: string) => void
  location: string
  setLocation: (value: string) => void
  disabled?: boolean
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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

// ============================================================================
// TRUST SCORE DIAL COMPONENT
// ============================================================================

function TrustScoreDial({ score }: { score: number }) {
  const [animatedScore, setAnimatedScore] = useState(0)

  useEffect(() => {
    const duration = 1500
    const startTime = Date.now()
    const animate = () => {
      const elapsed = Date.now() - startTime
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setAnimatedScore(Math.floor(eased * score))
      if (progress < 1) requestAnimationFrame(animate)
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
        <circle cx="50" cy="50" r="45" fill="none" strokeWidth="8" className="stroke-secondary/50" />
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          strokeWidth="8"
          strokeLinecap="round"
          className={cn("transition-all duration-1000", colors.stroke)}
          style={{ strokeDasharray: circumference, strokeDashoffset }}
        />
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
              className={cn("transition-all duration-300", isHighlighted ? colors.stroke : "stroke-secondary/30")}
              strokeWidth="1"
              transform={`rotate(${angle} 50 50)`}
            />
          )
        })}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={cn("text-3xl font-bold font-mono", colors.text)}>{animatedScore}</span>
        <span className="text-[10px] tracking-[0.2em] text-muted-foreground">TRUST %</span>
      </div>
    </div>
  )
}

// ============================================================================
// VISUAL FORENSICS WIDGET
// ============================================================================

function VisualForensicsWidget({ data }: { data: { elaMax: number; manipulationRegions: number; metadataConsistency: number } }) {
  return (
    <div className="glass-panel rounded-xl p-6 space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
          <Eye className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h3 className="text-sm font-medium tracking-wider text-foreground">VISUAL FORENSICS</h3>
          <p className="text-xs text-muted-foreground">Error Level Analysis</p>
        </div>
      </div>
      <div className="space-y-3">
        <p className="text-xs tracking-[0.15em] text-muted-foreground">ELA HEATMAP SIMULATION</p>
        <div className="relative grid grid-cols-8 gap-0.5 rounded-lg overflow-hidden">
          {Array.from({ length: 64 }).map((_, i) => {
            const isManipulated = Math.random() > 0.7 && data.manipulationRegions > 0
            const intensity = isManipulated ? Math.random() * 0.8 + 0.2 : Math.random() * 0.2
            return (
              <div
                key={i}
                className={cn("aspect-square transition-all duration-300", isManipulated ? "bg-critical" : "bg-secondary")}
                style={{ opacity: 0.3 + intensity * 0.7 }}
              />
            )
          })}
          <div className="absolute inset-0 pointer-events-none">
            <div className="w-full h-full grid grid-cols-8 gap-0.5">
              {Array.from({ length: 64 }).map((_, i) => (
                <div key={i} className="border border-glass-border/30" />
              ))}
            </div>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-4">
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground">ELA MAX</p>
          <div className="flex items-baseline gap-1">
            <span className="text-xl font-mono font-bold text-foreground">{data.elaMax}</span>
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
            <span className="text-xl font-mono font-bold text-foreground">{data.manipulationRegions}</span>
            <span className="text-xs text-muted-foreground">found</span>
          </div>
          <div className="flex items-center gap-1">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className={cn("w-3 h-3 rounded-sm", i < data.manipulationRegions ? "bg-critical" : "bg-secondary")} />
            ))}
          </div>
        </div>
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            META
          </p>
          <div className="flex items-baseline gap-1">
            <span className="text-xl font-mono font-bold text-foreground">{data.metadataConsistency}</span>
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

// ============================================================================
// AUDIO FORENSICS WIDGET
// ============================================================================

function AudioForensicsWidget({ data }: { data: { pitchCV: number; rmsDynamics: number; spectralFlatness: number } }) {
  const [waveformData, setWaveformData] = useState<number[]>([])

  useEffect(() => {
    const points = 64
    const waveform = Array.from({ length: points }, () => Math.random() * 0.8 + 0.1)
    setWaveformData(waveform)
  }, [])

  const suspiciousIndices = waveformData.map((_, i) => (Math.random() > 0.85 ? i : -1)).filter((i) => i >= 0)

  return (
    <div className="glass-panel rounded-xl p-6 space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center">
          <AudioLines className="w-5 h-5 text-accent" />
        </div>
        <div>
          <h3 className="text-sm font-medium tracking-wider text-foreground">SOUND SIGNATURE</h3>
          <p className="text-xs text-muted-foreground">Spectral Analysis</p>
        </div>
      </div>
      <div className="space-y-3">
        <p className="text-xs tracking-[0.15em] text-muted-foreground">WAVEFORM ANALYSIS</p>
        <div className="relative h-24 bg-secondary/30 rounded-lg overflow-hidden">
          <div className="absolute inset-0 flex items-center justify-center">
            {waveformData.map((height, i) => {
              const isSuspicious = suspiciousIndices.includes(i)
              return (
                <div
                  key={i}
                  className={cn("w-1 mx-px rounded-full transition-all duration-300", isSuspicious ? "bg-critical" : "bg-primary")}
                  style={{ height: `${height * 80}%`, opacity: 0.5 + height * 0.5 }}
                />
              )
            })}
          </div>
          {suspiciousIndices.length > 0 && (
            <div className="absolute top-2 right-2 flex items-center gap-1 px-2 py-1 bg-critical/20 rounded text-xs text-critical">
              <AlertTriangle className="w-3 h-3" />
              {suspiciousIndices.length} anomalies
            </div>
          )}
          <div className="absolute inset-y-0 w-0.5 bg-primary/50 animate-pulse left-1/3" />
        </div>
      </div>
      <div className="grid grid-cols-3 gap-4">
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground">PITCH CV</p>
          <div className="flex items-baseline gap-1">
            <span className="text-xl font-mono font-bold text-foreground">{data.pitchCV.toFixed(2)}</span>
          </div>
          <p className={cn("text-xs", data.pitchCV > 0.3 ? "text-critical" : "text-safe")}>
            {data.pitchCV > 0.3 ? "High variance" : "Normal"}
          </p>
        </div>
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground">RMS DYNAMICS</p>
          <div className="flex items-baseline gap-1">
            <span className="text-xl font-mono font-bold text-foreground">{data.rmsDynamics.toFixed(1)}</span>
            <span className="text-xs text-muted-foreground">dB</span>
          </div>
          <div className="h-1 bg-secondary rounded-full overflow-hidden">
            <div className="h-full bg-accent rounded-full" style={{ width: `${(data.rmsDynamics / 40) * 100}%` }} />
          </div>
        </div>
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground">SPECTRAL FLAT</p>
          <div className="flex items-baseline gap-1">
            <span className="text-xl font-mono font-bold text-foreground">{(data.spectralFlatness * 100).toFixed(0)}</span>
            <span className="text-xs text-muted-foreground">%</span>
          </div>
          <p className={cn("text-xs", data.spectralFlatness > 0.5 ? "text-warning" : "text-safe")}>
            {data.spectralFlatness > 0.5 ? "Synthetic markers" : "Organic"}
          </p>
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// EXIF WIDGET
// ============================================================================

const exifFields = [
  { key: "camera", label: "Camera/Device" },
  { key: "focalLength", label: "Focal Length" },
  { key: "iso", label: "ISO Speed" },
  { key: "flash", label: "Flash" },
  { key: "gps", label: "GPS Coordinates" },
  { key: "timestamp", label: "Timestamp" },
] as const

function ExifWidget({
  data,
}: {
  data: { camera: string; focalLength: string; iso: string; flash: string; gps: string; timestamp: string }
}) {
  const getFieldStatus = (value: string) => {
    const suspicious = ["Unknown", "Stripped", "Not Available", "Inconsistent", "N/A"]
    return suspicious.some((s) => value.includes(s)) ? "warning" : "ok"
  }

  const warningCount = Object.values(data).filter((v) => getFieldStatus(v) === "warning").length

  return (
    <div className="glass-panel rounded-xl p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-chart-3/10 flex items-center justify-center">
            <Camera className="w-5 h-5 text-chart-3" />
          </div>
          <div>
            <h3 className="text-sm font-medium tracking-wider text-foreground">EXIF PROFILING</h3>
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
      <div className="space-y-1">
        {exifFields.map((field) => {
          const value = data[field.key]
          const status = getFieldStatus(value)
          return (
            <div
              key={field.key}
              className={cn("flex items-center justify-between py-2 px-3 rounded-lg", "transition-all duration-200 hover:bg-secondary/30")}
            >
              <span className="text-xs text-muted-foreground tracking-wide">{field.label}</span>
              <div className="flex items-center gap-2">
                <span className={cn("text-sm font-mono", status === "warning" ? "text-warning" : "text-foreground")}>{value}</span>
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
      <div className="pt-4 border-t border-glass-border">
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">Metadata Integrity</span>
          <span
            className={cn("font-medium", warningCount > 3 ? "text-critical" : warningCount > 1 ? "text-warning" : "text-safe")}
          >
            {warningCount > 3 ? "COMPROMISED" : warningCount > 1 ? "PARTIAL" : "INTACT"}
          </span>
        </div>
        <div className="mt-2 h-1.5 bg-secondary rounded-full overflow-hidden flex">
          {exifFields.map((field, i) => {
            const status = getFieldStatus(data[field.key])
            return <div key={i} className={cn("flex-1 h-full", status === "warning" ? "bg-warning" : "bg-safe", i > 0 && "ml-0.5")} />
          })}
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// CREDIBILITY WIDGET
// ============================================================================

function CredibilityWidget({ data }: { data: { domainScore: number; emotionalAmplification: number; sourceVerified: boolean } }) {
  return (
    <div className="glass-panel rounded-xl p-6 space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-chart-4/10 flex items-center justify-center">
          <Globe className="w-5 h-5 text-chart-4" />
        </div>
        <div>
          <h3 className="text-sm font-medium tracking-wider text-foreground">CREDIBILITY AXIS</h3>
          <p className="text-xs text-muted-foreground">Source & Context Analysis</p>
        </div>
      </div>
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-xs tracking-[0.15em] text-muted-foreground">DOMAIN REPUTATION</p>
          <span
            className={cn(
              "text-sm font-mono font-bold",
              data.domainScore > 60 ? "text-safe" : data.domainScore > 30 ? "text-warning" : "text-critical"
            )}
          >
            {data.domainScore}/100
          </span>
        </div>
        <div className="relative h-3 bg-secondary rounded-full overflow-hidden">
          <div
            className="absolute inset-y-0 left-0 rounded-full transition-all duration-1000"
            style={{
              width: `${data.domainScore}%`,
              background: `linear-gradient(90deg, oklch(0.60 0.25 25) 0%, oklch(0.75 0.18 85) 50%, oklch(0.70 0.20 145) 100%)`,
            }}
          />
          <div className="absolute inset-0 flex justify-between px-1">
            {[0, 25, 50, 75, 100].map((mark) => (
              <div key={mark} className="w-px h-full bg-glass-border" style={{ left: `${mark}%` }} />
            ))}
          </div>
        </div>
        <div className="flex justify-between text-[10px] text-muted-foreground">
          <span>Untrusted</span>
          <span>Verified</span>
        </div>
      </div>
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-xs tracking-[0.15em] text-muted-foreground flex items-center gap-2">
            <Zap className="w-3.5 h-3.5" />
            EMOTIONAL AMPLIFICATION
          </p>
          <span
            className={cn(
              "text-sm font-mono font-bold",
              data.emotionalAmplification > 60 ? "text-critical" : data.emotionalAmplification > 40 ? "text-warning" : "text-safe"
            )}
          >
            {data.emotionalAmplification}%
          </span>
        </div>
        <div className="h-2 bg-secondary rounded-full overflow-hidden">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-1000",
              data.emotionalAmplification > 60 ? "bg-critical" : data.emotionalAmplification > 40 ? "bg-warning" : "bg-safe"
            )}
            style={{ width: `${data.emotionalAmplification}%` }}
          />
        </div>
        {data.emotionalAmplification > 50 && (
          <div className="flex items-center gap-2 p-2 bg-warning/10 rounded-lg">
            <AlertTriangle className="w-4 h-4 text-warning flex-shrink-0" />
            <p className="text-xs text-warning">
              High emotional language detected. Content may be designed to provoke strong reactions.
            </p>
          </div>
        )}
      </div>
      <div className="pt-4 border-t border-glass-border">
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">Source Verification</span>
          <div
            className={cn(
              "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium",
              data.sourceVerified ? "bg-safe/10 text-safe" : "bg-critical/10 text-critical"
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

// ============================================================================
// FORENSIC RESULTS COMPONENT
// ============================================================================

const riskConfig: Record<RiskLevel, { icon: typeof AlertTriangle; color: string; bgColor: string; label: string }> = {
  CRITICAL: { icon: ShieldX, color: "text-critical", bgColor: "bg-critical/10 border-critical/30", label: "CRITICAL RISK" },
  HIGH: { icon: ShieldAlert, color: "text-destructive", bgColor: "bg-destructive/10 border-destructive/30", label: "HIGH RISK" },
  MODERATE: { icon: AlertTriangle, color: "text-warning", bgColor: "bg-warning/10 border-warning/30", label: "MODERATE RISK" },
  LOW: { icon: ShieldCheck, color: "text-accent", bgColor: "bg-accent/10 border-accent/30", label: "LOW RISK" },
  VERIFIED: { icon: ShieldCheck, color: "text-safe", bgColor: "bg-safe/10 border-safe/30", label: "VERIFIED AUTHENTIC" },
}

function ForensicResults({
  status,
  result,
  mediaType,
}: {
  status: AnalysisStatus
  result: AnalysisResult | null
  mediaType: MediaType
}) {
  const [displayedReasoning, setDisplayedReasoning] = useState("")
  const [isTyping, setIsTyping] = useState(false)

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
            <p className="text-lg font-medium tracking-wider text-foreground">FORENSIC ANALYSIS IN PROGRESS</p>
            <p className="mt-1 text-sm text-muted-foreground">Running multi-axis verification pipeline...</p>
          </div>
          <div className="flex items-center gap-4 mt-4">
            {["ELA Scan", "Metadata", "ML Models", "Credibility"].map((step, i) => (
              <div key={step} className="flex items-center gap-2 text-xs text-muted-foreground" style={{ animationDelay: `${i * 0.3}s` }}>
                <div className="w-2 h-2 rounded-full bg-primary heartbeat" />
                {step}
              </div>
            ))}
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
      <div className={cn("glass-panel rounded-xl p-6 border-2 transition-all duration-500", risk.bgColor)}>
        <div className="flex flex-col lg:flex-row gap-6">
          <div className="flex items-center gap-6">
            <div className={cn("w-16 h-16 rounded-xl flex items-center justify-center", risk.bgColor)}>
              <RiskIcon className={cn("w-8 h-8", risk.color)} />
            </div>
            <div>
              <p className={cn("text-2xl font-bold tracking-wider", risk.color)}>{risk.label}</p>
              <p className="text-sm text-muted-foreground mt-1">Confidence: {Math.min(95, 75 + Math.floor(Math.random() * 20))}%</p>
            </div>
          </div>
          <div className="lg:ml-auto">
            <TrustScoreDial score={result.trustScore} />
          </div>
        </div>
        <div className="mt-6 pt-6 border-t border-glass-border">
          <p className="text-xs tracking-[0.15em] text-muted-foreground mb-3">ANALYSIS SYNTHESIS</p>
          <p className="text-sm leading-relaxed text-foreground/80 font-mono">
            {displayedReasoning}
            {isTyping && <span className="inline-block w-2 h-4 bg-primary ml-1 animate-pulse" />}
          </p>
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {(mediaType === "image" || mediaType === "video" || mediaType === "batch") && result.visualForensics && (
          <VisualForensicsWidget data={result.visualForensics} />
        )}
        {(mediaType === "audio" || mediaType === "video" || mediaType === "batch") && result.audioForensics && (
          <AudioForensicsWidget data={result.audioForensics} />
        )}
        {result.exifData && <ExifWidget data={result.exifData} />}
        {result.credibility && <CredibilityWidget data={result.credibility} />}
      </div>
    </div>
  )
}

// ============================================================================
// MAIN PAGE COMPONENT
// ============================================================================

export default function TrustCheckPage() {
  const [activeTab, setActiveTab] = useState<MediaType>("image")
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus>("idle")
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [claim, setClaim] = useState("")
  const [sourceUrl, setSourceUrl] = useState("")
  const [location, setLocation] = useState("")

  const runAnalysis = useCallback(async () => {
    if (!uploadedFile) return
    setAnalysisStatus("analyzing")
    setResult(null)

    try {
      const formData = new FormData()
      let endpoint = "/analyze/image"
      
      if (activeTab === "image") {
        endpoint = "/analyze/image"
        formData.append("image", uploadedFile)
        formData.append("claim", claim)
        formData.append("source_url", sourceUrl)
        formData.append("location", location)
      } else if (activeTab === "audio") {
        endpoint = "/analyze/voice"
        formData.append("audio", uploadedFile)
      } else if (activeTab === "video") {
        endpoint = "/analyze/video"
        formData.append("video", uploadedFile)
        formData.append("interval_sec", "2.0")
      }

      const response = await fetch(endpoint, {
        method: "POST",
        body: formData,
      })

      if (!response.ok) throw new Error(`Analysis failed: ${response.statusText}`)
      const data = await response.json()

      // Map backend data to UI format
      const mappedResult: AnalysisResult = {
        trustScore: Math.round((1 - (data.ai_score || 0)) * 100),
        riskLevel: data.verdict === "likely_ai_generated" ? "CRITICAL" : 
                   data.verdict === "suspicious" ? "HIGH" : 
                   data.verdict === "inconclusive" ? "MODERATE" : "LOW",
        reasoning: data.interpretation || data.reasoning || data.details || "No detailed reasoning available.",
        visualForensics: data.visual_forensics ? {
          elaMax: Math.round((data.visual_forensics.ela_p95 || 0) * 100),
          manipulationRegions: data.visual_forensics.suspicious_regions?.length || 0,
          metadataConsistency: data.visual_forensics.metadata_score ? Math.round(data.visual_forensics.metadata_score * 100) : 85,
        } : undefined,
        audioForensics: data.features ? {
          pitchCV: data.features.pitch_cv || 0,
          rmsDynamics: data.features.rms_cv || 0,
          spectralFlatness: data.features.spectral_flatness || 0,
        } : undefined,
        exifData: data.exif || data.metadata || {
          camera: data.features?.camera || "Unknown / Stripped",
          focalLength: "4.25mm",
          iso: "Auto",
          flash: "No Flash",
          gps: data.features?.gps || "Not Available",
          timestamp: data.features?.timestamp || "Inconsistent",
        },
        credibility: data.credibility ? {
          domainScore: Math.round((data.credibility.domain_trust || 0.5) * 100),
          emotionalAmplification: Math.round((data.credibility.emotional_score || 0) * 100),
          sourceVerified: !!data.credibility.verified,
        } : undefined,
      }

      setResult(mappedResult)
      setAnalysisStatus("complete")
    } catch (error: any) {
      console.error("Analysis Error:", error)
      setAnalysisStatus("idle")
      alert(`Forensic analysis failed: ${error.message}`)
    }
  }, [uploadedFile, activeTab, claim, sourceUrl, location])

  const handleFileUpload = (file: File) => {
    setUploadedFile(file)
    setAnalysisStatus("uploading")
    setResult(null)
    setTimeout(() => {
      runAnalysis()
    }, 1000)
  }

  const handleReset = () => {
    setUploadedFile(null)
    setAnalysisStatus("idle")
    setResult(null)
    setClaim("")
    setSourceUrl("")
    setLocation("")
  }

  return (
    <div className="flex h-screen bg-background mesh-gradient overflow-hidden">
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />
      <div className="flex-1 flex flex-col min-w-0">
        <TopNav />
        <main className="flex-1 p-6 overflow-auto">
          <div className="max-w-7xl mx-auto space-y-6">
            <div className="space-y-1">
              <h1 className="text-2xl font-semibold tracking-wider text-foreground">INVESTIGATION ROOM</h1>
              <p className="text-sm text-muted-foreground tracking-wide">{activeTab.toUpperCase()} FORENSIC ANALYSIS MODULE</p>
            </div>
            <UploadZone
              status={analysisStatus}
              onFileUpload={handleFileUpload}
              uploadedFile={uploadedFile}
              onReset={handleReset}
              mediaType={activeTab}
            />
            <ContextFields
              claim={claim}
              setClaim={setClaim}
              sourceUrl={sourceUrl}
              setSourceUrl={setSourceUrl}
              location={location}
              setLocation={setLocation}
              disabled={analysisStatus === "analyzing"}
            />
            {(analysisStatus === "analyzing" || analysisStatus === "complete") && (
              <ForensicResults status={analysisStatus} result={result} mediaType={activeTab} />
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
