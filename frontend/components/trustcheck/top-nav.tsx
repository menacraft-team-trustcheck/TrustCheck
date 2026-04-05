"use client"

import { useState, useEffect } from "react"
import { Activity, Database, Wifi, Clock, Bell, User } from "lucide-react"
import { cn } from "@/lib/utils"

interface StatusPill {
  id: string
  label: string
  value: string
  status: "online" | "degraded" | "offline"
  icon: typeof Activity
}

export function TopNav() {
  const [time, setTime] = useState<Date | null>(null)
  const [statuses, setStatuses] = useState<StatusPill[]>([
    { id: "api", label: "API Latency", value: "42ms", status: "online", icon: Activity },
    { id: "db", label: "Supabase", value: "Online", status: "online", icon: Database },
    { id: "ml", label: "ML Pipeline", value: "Active", status: "online", icon: Wifi },
  ])

  useEffect(() => {
    // Set initial time only on client to avoid hydration mismatch
    setTime(new Date())
    
    const interval = setInterval(() => {
      setTime(new Date())
      // Simulate fluctuating latency
      setStatuses((prev) =>
        prev.map((s) => ({
          ...s,
          value:
            s.id === "api"
              ? `${Math.floor(Math.random() * 30) + 35}ms`
              : s.value,
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
      {/* Left: Status Pills */}
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
                  <div
                    className={cn(
                      "w-2 h-2 rounded-full heartbeat",
                      getStatusColor(status.status)
                    )}
                  />
                </div>
                <Icon className="w-3.5 h-3.5 text-muted-foreground hidden md:block" />
                <span className="text-xs text-muted-foreground hidden lg:block">
                  {status.label}:
                </span>
                <span className="text-xs font-mono text-foreground">
                  {status.value}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Right: Time & Actions */}
      <div className="flex items-center gap-4">
        {/* Live Clock */}
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

        {/* Notifications */}
        <button className="relative p-2 rounded-lg hover:bg-secondary/50 transition-colors">
          <Bell className="w-5 h-5 text-muted-foreground" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-primary rounded-full pulse-ring" />
        </button>

        {/* User */}
        <button className="flex items-center gap-2 p-2 rounded-lg hover:bg-secondary/50 transition-colors">
          <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center border border-primary/30">
            <User className="w-4 h-4 text-primary" />
          </div>
        </button>
      </div>
    </header>
  )
}
