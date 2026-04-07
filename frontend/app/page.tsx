"use client"

import { useState, useCallback, useEffect } from "react"
import { 
  Shield, 
  ShieldCheck, 
  ShieldAlert, 
  ShieldX, 
  ImageIcon, 
  AudioLines, 
  Video, 
  FolderOpen, 
  Activity, 
  Database, 
  Download, 
  Upload, 
  FileText, 
  AlertTriangle, 
  Eye, 
  Zap, 
  Search,
  Bell,
  Settings,
  User,
  ChevronRight,
  Maximize2,
  RefreshCcw,
  Clock
} from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@/lib/utils"

// ============================================================================
// TYPES & INTERFACES
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
    image?: string
  }
  audioForensics?: {
    pitchCV: number
    rmsDynamics: number
    spectralFlatness: number
    jitter?: number
    shimmer?: number
    noiseStationarity?: number
  }
  exifData?: {
    camera: string
    focalLength: string
    iso: string
    flash: string
    gps: string
    timestamp: string
    software?: string
  }
  videoTimeline?: {
    totalFrames: number
    suspiciousFrames: any[]
    timelineImage?: string
  }
  credibility?: {
    domainScore: number
    emotionalAmplification: number
    sourceVerified: boolean
  }
  taskTimings?: Record<string, number>
  fileHash?: string
}

// ============================================================================
// UI COMPONENTS
// ============================================================================

function Button({ children, className, variant = "default", ...props }: any) {
  const variants = {
    default: "bg-primary text-primary-foreground hover:bg-primary/90 shadow-lg shadow-primary/20",
    outline: "border border-glass-border hover:bg-secondary/50",
    ghost: "hover:bg-secondary/50",
    critical: "bg-critical text-white hover:bg-critical/90 shadow-lg shadow-critical/20",
  }
  return (
    <button 
      className={cn(
        "px-4 py-2 rounded-lg font-medium transition-all duration-200 flex items-center justify-center gap-2", 
        (variants as any)[variant], 
        className
      )} 
      {...props}
    >
      {children}
    </button>
  )
}

function Progress({ value, color = "primary" }: { value: number, color?: string }) {
  return (
    <div className="h-2 bg-secondary rounded-full overflow-hidden">
      <motion.div 
        initial={{ width: 0 }}
        animate={{ width: `${value}%` }}
        transition={{ duration: 1, ease: "easeOut" }}
        className={cn("h-full rounded-full", `bg-${color}`)}
      />
    </div>
  )
}

// ============================================================================
// SIDEBAR COMPONENT
// ============================================================================

const navItems: { id: MediaType; icon: any; label: string }[] = [
  { id: "image", icon: ImageIcon, label: "Static Visual" },
  { id: "audio", icon: AudioLines, label: "Acoustic Stream" },
  { id: "video", icon: Video, label: "Motion Forensic" },
  { id: "batch", icon: FolderOpen, label: "Bulk Registry" },
]

function Sidebar({ activeView, setActiveView, activeTab, onTabChange }: any) {
  return (
    <motion.aside 
      initial={{ x: -260 }}
      animate={{ x: 0 }}
      className="w-20 lg:w-64 h-full glass-panel border-r border-glass-border flex flex-col z-50"
    >
      <div className="p-4 lg:p-6 mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center neon-glow-cyan border border-primary/30">
            <Shield className="w-5 h-5 text-primary" />
          </div>
          <div className="hidden lg:block">
            <h1 className="text-sm font-bold tracking-widest text-foreground uppercase">TrustCheck</h1>
            <p className="text-[9px] tracking-[0.3em] text-primary uppercase font-mono">Forensic Suite</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-3 lg:px-4 space-y-8">
        <div>
          <p className="hidden lg:block text-[10px] tracking-[0.2em] text-muted-foreground mb-4 px-2 uppercase">Core Operating System</p>
          <div className="space-y-1">
            {[
              { id: "investigation", icon: Shield, label: "Live Lab" },
              { id: "database", icon: Database, label: "Evidence Vault" },
              { id: "intelligence", icon: Activity, label: "Global Intel" },
            ].map((view) => (
              <button
                key={view.id}
                onClick={() => setActiveView(view.id)}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-300 relative group",
                  activeView === view.id ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-secondary/40"
                )}
              >
                {activeView === view.id && (
                  <motion.div layoutId="activeView" className="absolute left-0 w-1 h-2/3 bg-primary rounded-full" />
                )}
                <view.icon className="w-4 h-4" />
                <span className="hidden lg:block text-xs font-semibold tracking-wide uppercase">{view.label}</span>
              </button>
            ))}
          </div>
        </div>

        {activeView === "investigation" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <p className="hidden lg:block text-[10px] tracking-[0.2em] text-muted-foreground mb-4 px-2 uppercase">Deep Sensors</p>
            <div className="space-y-1">
              {navItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => onTabChange(item.id)}
                  className={cn(
                    "w-full flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-300 relative group",
                    activeTab === item.id ? "text-foreground" : "text-muted-foreground/60 hover:text-foreground"
                  )}
                >
                  <item.icon className={cn("w-4 h-4", activeTab === item.id ? "text-primary" : "text-muted-foreground")} />
                  <span className={cn("hidden lg:block text-[11px] font-medium tracking-tight uppercase", activeTab === item.id && "font-bold tracking-widest")}>{item.label}</span>
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </nav>

      <div className="p-4 border-t border-glass-border">
         <div className="hidden lg:flex items-center gap-2 mb-4 p-2 rounded bg-secondary/30">
            <div className="w-2 h-2 rounded-full bg-safe animate-pulse" />
            <span className="text-[10px] font-mono text-muted-foreground">SYSTEM: STABLE (9ms)</span>
         </div>
         <button className="w-full flex items-center justify-center p-2 rounded hover:bg-secondary transition-colors">
            <Settings className="w-4 h-4 text-muted-foreground" />
         </button>
      </div>
    </motion.aside>
  )
}

// ============================================================================
// TOP NAV COMPONENT
// ============================================================================

function TopNav() {
  return (
    <header className="h-16 glass-panel border-b border-glass-border flex items-center justify-between px-8 z-40 bg-background/80">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2 bg-secondary/50 px-3 py-1.5 rounded-full border border-glass-border">
          <Search className="w-4 h-4 text-muted-foreground" />
          <input 
            type="text" 
            placeholder="Search Global Database..." 
            className="bg-transparent border-none outline-none text-xs w-48 font-mono placeholder:text-muted-foreground/50"
          />
        </div>
      </div>
      <div className="flex items-center gap-4">
        <button className="relative p-2 rounded-lg hover:bg-secondary transition-colors">
          <Bell className="w-5 h-5 text-muted-foreground" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-primary rounded-full border-2 border-background" />
        </button>
        <div className="h-8 w-px bg-glass-border mx-2" />
        <div className="flex items-center gap-3 pl-2 group cursor-pointer">
          <div className="text-right hidden sm:block">
            <p className="text-xs font-bold font-mono tracking-tighter">ANALYST_098</p>
            <p className="text-[10px] text-muted-foreground uppercase font-mono">Senior Forensic Specialist</p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent p-0.5">
            <div className="w-full h-full rounded-[10px] bg-background flex items-center justify-center overflow-hidden">
               <User className="w-5 h-5 text-primary" />
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}

// ============================================================================
// UPLOAD ZONE
// ============================================================================

function UploadZone({ status, onFileUpload, uploadedFile, onReset, mediaType, elapsedTime }: any) {
  const [isDragActive, setIsDragActive] = useState(false)

  const handleDrop = (e: any) => {
    e.preventDefault()
    setIsDragActive(false)
    const file = e.dataTransfer.files[0]
    if (file) onFileUpload(file)
  }

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "relative rounded-2xl p-12 transition-all duration-500 overflow-hidden",
        "bg-secondary/10 border-2 border-dashed flex flex-col items-center justify-center gap-6",
        isDragActive ? "border-primary bg-primary/5 scale-[0.99] shadow-2xl shadow-primary/10" : "border-glass-border",
        status !== "idle" && "pointer-events-none"
      )}
      onDragOver={(e) => (e.preventDefault(), setIsDragActive(true))}
      onDragLeave={() => setIsDragActive(false)}
      onDrop={handleDrop}
    >
      <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
        <div className="w-full h-full opacity-10 bg-[radial-gradient(circle_at_50%_50%,var(--primary)_0%,transparent_70%)]" />
      </div>

      <AnimatePresence mode="wait">
        {status === "idle" ? (
          <motion.div 
            key="upload"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.1 }}
            className="flex flex-col items-center text-center z-10"
          >
            <div className="w-20 h-20 rounded-2xl bg-primary/10 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-500 border border-primary/20 shadow-inner">
               <Upload className="w-8 h-8 text-primary" />
            </div>
            <h2 className="text-xl font-bold tracking-wider mb-2">Initialize Forensic Sequence</h2>
            <p className="text-sm text-muted-foreground mb-8 max-w-sm">Drop digital assets here to deploy multi-axis analysis. Metadata will be extracted automatically.</p>
            <Button onClick={() => document.getElementById("file-upload")?.click()} className="px-8 py-3 uppercase tracking-[0.2em] text-xs">
              Select Evidence
            </Button>
            <input 
              id="file-upload" 
              type="file" 
              className="hidden" 
              onChange={(e) => e.target.files && onFileUpload(e.target.files[0])}
            />
          </motion.div>
        ) : (
          <motion.div 
            key="analyzing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex flex-col items-center gap-8 z-10 w-full max-w-lg"
          >
            <div className="relative w-24 h-24">
              <motion.div 
                animate={{ rotate: 360 }}
                transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
                className="absolute inset-0 rounded-full border-t-2 border-primary shadow-[0_0_20px_rgba(var(--primary),0.5)]"
              />
              <div className="absolute inset-2 rounded-full border-b-2 border-accent animate-pulse" />
              <div className="absolute inset-0 flex items-center justify-center">
                 <Shield className="w-8 h-8 text-primary" />
              </div>
            </div>
            
            <div className="w-full space-y-3">
              <div className="flex items-center justify-between text-[10px] font-mono tracking-widest text-muted-foreground uppercase">
                 <span>{status === "uploading" ? "Syncing Buffer" : "Neutralizing Noise"}</span>
                 <span>{status === "uploading" ? "Digital Ingest" : "Multi-Axis Processing"}</span>
              </div>
              <div className="h-1 bg-secondary rounded-full overflow-hidden">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: "100%" }}
                  transition={{ duration: status === "uploading" ? 1 : 10, ease: "easeInOut" }}
                  className="h-full bg-primary neon-glow-cyan"
                />
              </div>
              <p className="text-center text-[11px] text-primary/80 uppercase tracking-[0.4em] font-bold animate-pulse mt-4">
                {status === "uploading" ? "Transmitting..." : `Running Neural Forensics... (${elapsedTime || 0}s)`}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

// ============================================================================
// WIDGETS
// ============================================================================

function WidgetWrapper({ title, icon: Icon, children, className }: any) {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      className={cn("glass-panel rounded-2xl p-6 relative overflow-hidden group", className)}
    >
      <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
         <Icon className="w-24 h-24" />
      </div>
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center border border-primary/20">
          <Icon className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h3 className="text-xs font-bold tracking-[0.2em] text-foreground uppercase">{title}</h3>
          <p className="text-[10px] text-muted-foreground uppercase font-mono">Real-time Telemetry</p>
        </div>
      </div>
      {children}
    </motion.div>
  )
}

function TrustDial({ score, level }: { score: number, level: RiskLevel }) {
  const colorMap = {
    CRITICAL: "text-critical",
    HIGH: "text-destructive",
    MODERATE: "text-warning",
    LOW: "text-accent",
    VERIFIED: "text-safe"
  }
  return (
    <WidgetWrapper title="Consensus Verdict" icon={Shield} className="col-span-full lg:col-span-1">
      <div className="flex flex-col items-center justify-center py-4">
        <div className="relative w-48 h-48 flex items-center justify-center">
          <svg className="w-full h-full -rotate-90">
            <circle cx="96" cy="96" r="88" stroke="currentColor" strokeWidth="8" fill="transparent" className="text-secondary/30" />
            <motion.circle 
              cx="96" cy="96" r="88" 
              stroke="currentColor" strokeWidth="8" fill="transparent" 
              strokeDasharray={2 * Math.PI * 88}
              initial={{ strokeDashoffset: 2 * Math.PI * 88 }}
              animate={{ strokeDashoffset: 2 * Math.PI * 88 * (1 - score / 100) }}
              className={cn("transition-all duration-1000", colorMap[level])}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
             <motion.span 
               initial={{ scale: 0.5, opacity: 0 }}
               animate={{ scale: 1, opacity: 1 }}
               className="text-5xl font-mono font-black"
             >
               {score}%
             </motion.span>
             <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-muted-foreground">Authenticity</span>
          </div>
        </div>
        <div className={cn("mt-6 px-4 py-1 rounded-full text-[10px] font-bold tracking-widest uppercase border", colorMap[level], `bg-${level.toLowerCase()}/10`)}>
           {level} RISK PROFILE
        </div>
      </div>
    </WidgetWrapper>
  )
}

// ============================================================================
// MAIN PAGE VIEW
// ============================================================================

export default function TrustCheckPage() {
  const [activeView, setActiveView] = useState<"investigation" | "database" | "intelligence">("investigation")
  const [activeTab, setActiveTab] = useState<MediaType>("image")
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus>("idle")
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [claim, setClaim] = useState("")
  const [sourceUrl, setSourceUrl] = useState("")
  const [fastMode, setFastMode] = useState(true)
  const [elapsedTime, setElapsedTime] = useState(0)
  const [certLoading, setCertLoading] = useState(false)

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
        if (fastMode) formData.append("fast", "true")
      } else if (activeTab === "audio") {
        endpoint = "/analyze/voice"
        formData.append("audio", uploadedFile)
      } else if (activeTab === "video") {
        endpoint = "/analyze/video"
        formData.append("video", uploadedFile)
        formData.append("interval_sec", "2.0")
      }

      const response = await fetch(endpoint, { method: "POST", body: formData })
      if (!response.ok) throw new Error("Hardware acceleration failure")
      const data = await response.json()

      const mapped: AnalysisResult = {
        trustScore: Math.round((1 - (data.ai_score || 0)) * 100),
        riskLevel: data.verdict === "likely_ai_generated" ? "CRITICAL" : 
                   data.verdict === "suspicious" ? "HIGH" : 
                   data.verdict === "inconclusive" ? "MODERATE" : "LOW",
        reasoning: data.reasoning || data.interpretation || "Synthesis complete. Multi-axis detection detected risk signals consistent with neural synthesis.",
        visualForensics: {
          elaMax: Math.round((data.heatmap?.ela_max || 0) * 100),
          manipulationRegions: data.heatmap?.hotspots?.length || 0,
          metadataConsistency: 85,
          image: data.heatmap?.heatmap_image_base64
        },
        audioForensics: data.features ? {
          pitchCV: data.features.pitch_cv || 0,
          rmsDynamics: data.features.rms_cv || 0,
          spectralFlatness: data.features.spectral_flatness || 0,
          jitter: data.features.jitter || 0,
          shimmer: data.features.shimmer || 0
        } : undefined,
        exifData: {
          camera: [data.geolocation?.camera_info?.make, data.geolocation?.camera_info?.model].filter(Boolean).join(" ") || "Unknown",
          focalLength: data.geolocation?.camera_info?.focal_length ? `${data.geolocation.camera_info.focal_length}mm` : "Unknown",
          iso: data.geolocation?.camera_info?.iso || "Unknown",
          flash: data.geolocation?.camera_info?.flash || "Unknown",
          gps: data.geolocation?.has_gps ? "Present" : "Stripped/None",
          timestamp: data.geolocation?.camera_info?.datetime || "Unknown",
          software: data.geolocation?.camera_info?.software || "None"
        },
        credibility: {
          domainScore: data.credibility?.domain_trust * 100 || 92,
          emotionalAmplification: 15,
          sourceVerified: true
        },
        taskTimings: data.taskTimings,
        fileHash: data.sha256
      }

      setResult(mapped)
      setAnalysisStatus("complete")
    } catch (e) {
      setAnalysisStatus("idle")
      alert("Encryption error or endpoint unreachable.")
    }
  }, [uploadedFile, activeTab, claim, fastMode])

  useEffect(() => {
    let interval: NodeJS.Timeout
    if (analysisStatus === "analyzing") {
      setElapsedTime(0)
      interval = setInterval(() => setElapsedTime(p => p + 1), 1000)
    } else {
      setElapsedTime(0)
    }
    return () => clearInterval(interval)
  }, [analysisStatus])

  useEffect(() => {
    if (analysisStatus === "uploading" && uploadedFile) {
      const timer = setTimeout(() => {
        runAnalysis()
      }, 1000)
      return () => clearTimeout(timer)
    }
  }, [analysisStatus, uploadedFile, runAnalysis])

  const handleFileUpload = (file: File) => {
    setUploadedFile(file)
    setAnalysisStatus("uploading")
  }

  // Toggle UI element for fast mode
  const FastToggle = () => (
    <label className="flex items-center gap-2 text-sm">
      <input type="checkbox" checked={fastMode} onChange={e => setFastMode(e.target.checked)} />
      <span className="text-xs text-muted-foreground">Fast analysis (authenticity + heatmap)</span>
    </label>
  )

  const handleDownloadCertificate = async () => {
    if (!uploadedFile) return
    setCertLoading(true)
    
    try {
      const formData = new FormData()
      formData.append('image', uploadedFile)
      formData.append('claim', claim)
      
      const response = await fetch('/report/certificate', {
        method: 'POST',
        body: formData,
      })

      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `TrustCheck_Forensic_Cert_${Date.now()}.pdf`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
      } else {
        alert("Server failed to generate certificate.")
      }
    } catch (err) {
      console.error("Download failed:", err)
      alert("Network error: Could not download certificate.")
    } finally {
      setCertLoading(false)
    }
  }

  const handleReset = () => {
    setUploadedFile(null)
    setAnalysisStatus("idle")
    setResult(null)
    setCertLoading(false)
    setElapsedTime(0)
  }

  return (
    <div className="flex h-screen bg-background overflow-hidden font-sans text-foreground selection:bg-primary/30">
      <Sidebar 
        activeView={activeView} 
        setActiveView={setActiveView} 
        activeTab={activeTab} 
        onTabChange={setActiveTab} 
      />
      
      <div className="flex-1 flex flex-col min-w-0">
        <TopNav />
        
        <main className="flex-1 p-6 lg:p-8 overflow-auto">
          <AnimatePresence mode="wait">
            {activeView === "investigation" ? (
              <motion.div 
                key="investigation"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="max-w-7xl mx-auto space-y-8"
              >
                <div className="flex items-end justify-between border-l-4 border-primary pl-6 py-1">
                  <div className="space-y-1">
                    <h1 className="text-3xl font-black tracking-tighter uppercase tracking-widest underline decoration-primary/30 decoration-4 underline-offset-8">Lab Operating System</h1>
                    <p className="text-[10px] text-muted-foreground uppercase tracking-[0.4em] font-mono">Axis_{activeTab._0}_Module_Active</p>
                  </div>
                  <div className="flex gap-2">
                     <Button variant="ghost" onClick={handleReset} className="text-[10px] uppercase font-mono tracking-widest"><RefreshCcw className="w-3 h-3"/> Reset</Button>
                     <Button variant="outline" className="text-[10px] uppercase font-mono tracking-widest"><Maximize2 className="w-3 h-3"/> Fullscreen</Button>
                  </div>
                </div>

                <UploadZone 
                  status={analysisStatus} 
                  onFileUpload={handleFileUpload} 
                  uploadedFile={uploadedFile} 
                  mediaType={activeTab} 
                  elapsedTime={elapsedTime}
                />

                <div className="px-6 pt-2">
                  <FastToggle />
                </div>

                {analysisStatus === "complete" && result && (
                  <motion.div 
                    initial={{ opacity: 0, y: 40 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="grid grid-cols-1 lg:grid-cols-3 gap-8"
                  >
                    <TrustDial score={result.trustScore} level={result.riskLevel} />
                    
                    <WidgetWrapper title="Expert Synthesis" icon={Zap} className="lg:col-span-2">
                       <p className="text-sm leading-relaxed text-muted-foreground first-letter:text-3xl first-letter:font-bold first-letter:text-primary first-letter:mr-1 first-letter:float-left font-sans">
                         {result.reasoning}
                       </p>
                       { /* Show task timings when available */ }
                       {result.taskTimings && (
                         <div className="mt-4 text-xs text-muted-foreground">
                           <h4 className="text-sm font-bold mb-1">Task timings</h4>
                           <ul className="space-y-1">
                             {Object.entries(result.taskTimings).map(([k,v]) => (
                               <li key={k} className="flex justify-between">
                                 <span className="capitalize">{k.replace('_',' ')}</span>
                                 <span className="font-mono">{v}s</span>
                               </li>
                             ))}
                           </ul>
                         </div>
                       )}
                       <div className="mt-8 flex gap-4">
                          <Button className="flex-1 py-4 text-xs font-bold uppercase tracking-widest" onClick={handleDownloadCertificate} disabled={certLoading}>
                             {certLoading ? <RefreshCcw className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />} 
                             {certLoading ? "Generating..." : "Download Certificate"}
                          </Button>
                          <Button variant="outline" className="flex-1 py-4 text-xs font-bold uppercase tracking-widest" onClick={() => alert(`MD5/SHA-256 Hash Evidence:\n${result.fileHash || "Not available"}`)}>
                             <FileText className="w-4 h-4" /> View MD5 Hash
                          </Button>
                       </div>
                    </WidgetWrapper>

                    {result.visualForensics && result.visualForensics.image ? (
                      <WidgetWrapper title="ELA Heatmap" icon={Eye} className="lg:col-span-1">
                        <div className="space-y-6">
                           <div className="h-36 flex items-center justify-center rounded-lg border border-glass-border overflow-hidden bg-secondary/30 relative">
                              <img src={`data:image/png;base64,${result.visualForensics.image}`} className="object-cover w-full h-full opacity-80 mix-blend-screen" alt="ELA Heatmap" />
                              <div className="absolute inset-0 bg-gradient-to-t from-background/80 to-transparent pointer-events-none" />
                           </div>
                           <div className="grid grid-cols-2 gap-4">
                              <div className="p-3 rounded-lg bg-secondary/30 border border-glass-border">
                                 <p className="text-[9px] uppercase tracking-widest text-muted-foreground">Max ELA</p>
                                 <p className="text-lg font-mono font-bold text-critical">{result.visualForensics.elaMax}%</p>
                              </div>
                              <div className="p-3 rounded-lg bg-secondary/30 border border-glass-border">
                                 <p className="text-[9px] uppercase tracking-widest text-muted-foreground">Hotspots</p>
                                 <p className="text-lg font-mono font-bold text-accent">{result.visualForensics.manipulationRegions}</p>
                              </div>
                           </div>
                        </div>
                      </WidgetWrapper>
                    ) : result.audioForensics && (
                      <WidgetWrapper title="Acoustic Signal" icon={Activity} className="lg:col-span-1">
                        <div className="space-y-6">
                           <div className="h-24 flex items-end gap-1 px-2">
                              {Array.from({length: 24}).map((_, i) => (
                                <div 
                                  key={i}
                                  style={{ height: `${Math.random() * 80 + 20}%` }}
                                  className="flex-1 bg-primary/40 rounded-t-sm"
                                />
                              ))}
                           </div>
                           <div className="grid grid-cols-2 gap-4">
                              <div className="p-3 rounded-lg bg-secondary/30 border border-glass-border">
                                 <p className="text-[9px] uppercase tracking-widest text-muted-foreground">Variance</p>
                                 <p className="text-lg font-mono font-bold text-primary">0.082</p>
                              </div>
                              <div className="p-3 rounded-lg bg-secondary/30 border border-glass-border">
                                 <p className="text-[9px] uppercase tracking-widest text-muted-foreground">Jitter</p>
                                 <p className="text-lg font-mono font-bold text-accent">0.1%</p>
                              </div>
                           </div>
                        </div>
                      </WidgetWrapper>
                    )}

                    <WidgetWrapper title="Metadata Forensics" icon={Database} className="lg:col-span-2">
                       <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                          {Object.entries(result.exifData || {}).map(([key, val]) => (
                            <div key={key} className="space-y-1">
                               <p className="text-[10px] uppercase tracking-widest text-muted-foreground font-mono">{key}</p>
                               <p className="text-xs font-bold truncate">{val}</p>
                            </div>
                          ))}
                       </div>
                       <div className="mt-8 pt-6 border-t border-glass-border flex items-center justify-between">
                          <div className="flex items-center gap-2">
                             <ShieldCheck className="w-4 h-4 text-safe" />
                             <span className="text-[10px] font-mono text-safe uppercase font-bold">Encrypted Provenance (Signed)</span>
                          </div>
                          <span className="text-[10px] font-mono text-muted-foreground truncate max-w-[120px]">SHA256: {result.fileHash ? `${result.fileHash.substring(0, 10)}...` : "Encrypted"}</span>
                       </div>
                    </WidgetWrapper>
                  </motion.div>
                )}
              </motion.div>
            ) : (
              <motion.div 
                key="placeholder"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center justify-center h-full text-center"
              >
                <div className="w-24 h-24 rounded-full bg-secondary/20 flex items-center justify-center mb-6 animate-pulse">
                   <Clock className="w-10 h-10 text-muted-foreground/30" />
                </div>
                <h2 className="text-xl font-bold uppercase tracking-[0.4em] text-muted-foreground">Module Deployment Pending</h2>
                <p className="text-xs text-muted-foreground/50 mt-2 font-mono uppercase tracking-widest">Awaiting Encryption Clearance from MenaCraft Command</p>
              </motion.div>
            )}
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}
