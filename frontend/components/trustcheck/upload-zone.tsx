"use client"

import { useCallback, useState } from "react"
import { cn } from "@/lib/utils"
import type { AnalysisStatus, MediaType } from "@/app/page"
import { Upload, FileImage, FileAudio, FileVideo, Files, X, Loader2, CheckCircle2 } from "lucide-react"
import { Button } from "@/components/ui/button"

interface UploadZoneProps {
  status: AnalysisStatus
  onFileUpload: (file: File) => void
  uploadedFile: File | null
  onReset: () => void
  mediaType: MediaType
}

const mediaConfig = {
  image: {
    icon: FileImage,
    accept: "image/*",
    label: "Images",
    formats: "PNG, JPEG, WEBP, GIF",
  },
  audio: {
    icon: FileAudio,
    accept: "audio/*",
    label: "Audio",
    formats: "MP3, WAV, OGG, FLAC",
  },
  video: {
    icon: FileVideo,
    accept: "video/*",
    label: "Video",
    formats: "MP4, MOV, AVI, WEBM",
  },
  batch: {
    icon: Files,
    accept: "image/*,audio/*,video/*",
    label: "Multiple Files",
    formats: "Images, Audio, Video",
  },
}

export function UploadZone({
  status,
  onFileUpload,
  uploadedFile,
  onReset,
  mediaType,
}: UploadZoneProps) {
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
      {/* Scanning overlay */}
      {isProcessing && (
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div className="absolute inset-0 bg-primary/5" />
          <div className="scanning-line absolute inset-y-0 w-full h-1 top-0" />
          <div
            className="scanning-line absolute inset-y-0 w-full h-1"
            style={{ animationDelay: "0.5s", top: "33%" }}
          />
          <div
            className="scanning-line absolute inset-y-0 w-full h-1"
            style={{ animationDelay: "1s", top: "66%" }}
          />
        </div>
      )}

      <div className="p-8 md:p-12">
        {status === "idle" ? (
          /* Idle State - Upload prompt */
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
              <p className="text-lg font-medium tracking-wide text-foreground">
                Drop {config.label} Here
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                or click to browse • {config.formats}
              </p>
            </div>
            <div className="mt-6 flex items-center gap-2">
              <Icon className="w-4 h-4 text-muted-foreground" />
              <span className="text-xs tracking-wider text-muted-foreground">
                MAX FILE SIZE: 100MB
              </span>
            </div>
          </label>
        ) : (
          /* Processing / Complete State */
          <div className="flex flex-col md:flex-row items-center gap-6">
            {/* File Preview */}
            <div className="w-24 h-24 rounded-xl bg-secondary/50 flex items-center justify-center relative">
              <Icon className="w-10 h-10 text-primary" />
              {status === "complete" && (
                <div className="absolute -bottom-2 -right-2 w-8 h-8 rounded-full bg-accent flex items-center justify-center">
                  <CheckCircle2 className="w-5 h-5 text-accent-foreground" />
                </div>
              )}
            </div>

            {/* File Info */}
            <div className="flex-1 text-center md:text-left">
              <p className="font-mono text-sm text-foreground truncate max-w-xs">
                {uploadedFile?.name || "sample_media.file"}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {uploadedFile
                  ? `${(uploadedFile.size / 1024 / 1024).toFixed(2)} MB • ${uploadedFile.type}`
                  : "Unknown size"}
              </p>
              <div className="mt-3 flex items-center justify-center md:justify-start gap-2">
                {isProcessing ? (
                  <>
                    <Loader2 className="w-4 h-4 text-primary animate-spin" />
                    <span className="text-sm text-primary font-medium tracking-wide">
                      {status === "uploading"
                        ? "UPLOADING..."
                        : "ANALYZING..."}
                    </span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-accent" />
                    <span className="text-sm text-accent font-medium tracking-wide">
                      ANALYSIS COMPLETE
                    </span>
                  </>
                )}
              </div>
            </div>

            {/* Reset Button */}
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
