"use client"

import { cn } from "@/lib/utils"
import type { MediaType } from "@/app/page"
import { ImageIcon, AudioLines, Video, FolderOpen, Shield, Settings, HelpCircle } from "lucide-react"

interface SidebarProps {
  activeTab: MediaType
  onTabChange: (tab: MediaType) => void
}

const navItems: { id: MediaType; icon: typeof ImageIcon; label: string }[] = [
  { id: "image", icon: ImageIcon, label: "Image" },
  { id: "audio", icon: AudioLines, label: "Audio" },
  { id: "video", icon: Video, label: "Video" },
  { id: "batch", icon: FolderOpen, label: "Batch" },
]

export function Sidebar({ activeTab, onTabChange }: SidebarProps) {
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
              {/* Active indicator */}
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
              
              {/* Scanning line animation on hover */}
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
