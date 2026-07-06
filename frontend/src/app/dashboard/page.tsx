"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { 
  Sparkles, 
  TrendingUp, 
  MessageSquare, 
  AlertTriangle, 
  FileText, 
  Check, 
  X,
  Play,
  HelpCircle,
  TrendingDown,
  Sparkle
} from "lucide-react";

export default function DashboardPage() {
  const stats = [
    { label: "Videos Analyzed", value: "124", icon: Play },
    { label: "Comments Processed", value: "3.2k", icon: MessageSquare },
    { label: "Questions Discovered", value: "482", icon: HelpCircle },
  ];

  const actions = [
    {
      id: 1,
      type: "alert",
      icon: AlertTriangle,
      iconBg: "bg-amber-100 text-amber-700",
      title: "Address setup confusion in next video",
      description: "Found 45 comments asking about the Godox light mounting bracket orientation. A 30-second clarification could reduce churn.",
      buttonText: "Add to Script"
    },
    {
      id: 2,
      type: "trend",
      icon: TrendingUp,
      iconBg: "bg-emerald-100 text-emerald-700",
      title: "Opportunity: 'Fujifilm Color Grades' trend",
      description: "High search volume (up 42%) among your core subscribers. Your 'Classic Chrome' preset video is perfectly positioned.",
      buttonText: "Analyze Keywords"
    },
    {
      id: 3,
      type: "opt",
      icon: Sparkle,
      iconBg: "bg-indigo-100 text-indigo-700",
      title: "Optimization: Title A/B Test recommendation",
      description: "\"Why I Switched\" is underperforming compared to your historical \"The Switch\" narrative titles.",
      buttonText: "Apply New Title"
    }
  ];

  return (
    <motion.div 
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col gap-8 text-on-surface"
    >
      {/* Welcome Bar Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-col">
          <h1 className="font-playfair text-3xl font-bold text-primary">Good morning, Creator</h1>
          <p className="text-on-surface-variant font-literata text-sm mt-1 max-w-xl leading-relaxed">
            Your audience is highly engaged with the 'Minimalist Setup' series. Here is your editorial pulse for today.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button className="px-5 py-2.5 rounded-full border border-outline-variant/30 text-xs font-semibold font-literata text-on-surface-variant hover:bg-surface-container hover:text-primary transition-all duration-150 cursor-pointer">
            Export Report
          </button>
          <button className="px-5 py-2.5 rounded-full bg-primary hover:bg-primary-container text-on-primary text-xs font-semibold font-literata transition-all duration-150 flex items-center gap-1.5 shadow-sm cursor-pointer">
            <span className="text-sm font-bold">+</span>
            <span>New Project</span>
          </button>
        </div>
      </div>

      {/* Main Grid: Today's Summary & Audience Health */}
      <div className="grid lg:grid-cols-3 gap-8 items-start">
        {/* Large Summary Card */}
        <div className="lg:col-span-2 bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-3xl p-8 shadow-sm flex flex-col justify-between min-h-[340px] relative overflow-hidden group hover:shadow-md transition-shadow">
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <div className="inline-flex items-center gap-2">
                <span className="ai-badge">AI Editorial</span>
                <span className="text-[10px] text-on-surface-variant/80 font-literata">June 24, 2026</span>
              </div>
            </div>
            
            <h2 className="font-playfair text-2xl font-bold text-primary">Today's Summary</h2>
            <p className="text-on-surface-variant font-literata text-sm leading-relaxed mt-1">
              Retention peaked at the 4:12 mark in your latest upload, coinciding with the technical deep-dive on focal lengths. However, a significant portion of commenters in the 'Budget Gear' video are expressing confusion regarding the mounting bracket setup. We suggest a short follow-up or a pinned comment to clarify the orientation.
            </p>
          </div>

          <div className="flex items-center gap-6 mt-8 border-t border-outline-variant/20 pt-6">
            <div className="flex items-center gap-2 text-xs font-literata text-emerald-700 font-medium">
              <TrendingUp className="w-4 h-4" />
              <span>+14% Retention</span>
            </div>
            <div className="flex items-center gap-2 text-xs font-literata text-amber-700 font-medium">
              <MessageSquare className="w-4 h-4" />
              <span>82 Unresolved Queries</span>
            </div>
          </div>

          {/* Magic Wand Visual Overlay */}
          <div className="absolute right-6 top-8 w-24 h-24 opacity-10 pointer-events-none group-hover:opacity-15 transition-opacity">
            <svg viewBox="0 0 100 100" className="w-full h-full fill-primary">
              <path d="M78.6 30.6c1-1 1-2.6 0-3.6L73 21.4c-1-1-2.6-1-3.6 0L24.8 66c-1 1-1 2.6 0 3.6l5.6 5.6c1 1 2.6 1 3.6 0l44.6-44.6zM88 40v4c0 1.1-.9 2-2 2s-2-.9-2-2v-4c0-1.1.9-2 2-2s2 .9 2 2zm-58 48v4c0 1.1-.9 2-2 2s-2-.9-2-2v-4c0-1.1.9-2 2-2s2 .9 2 2zm34-6c0-1.1.9-2 2-2h4c1.1 0 2 .9 2 2s-.9 2-2 2h-4c-1.1 0-2-.9-2-2z" />
            </svg>
          </div>
        </div>

        {/* Audience Health Card */}
        <div className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-3xl p-8 shadow-sm flex flex-col items-center justify-between min-h-[340px] hover:shadow-md transition-shadow">
          <div className="w-full flex items-center justify-between">
            <h3 className="font-playfair text-lg font-bold text-primary">Audience Health</h3>
            <button className="text-on-surface-variant hover:text-primary">
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <circle cx="12" cy="5" r="2" />
                <circle cx="12" cy="12" r="2" />
                <circle cx="12" cy="19" r="2" />
              </svg>
            </button>
          </div>

          {/* SVG Progress Circle */}
          <div className="relative w-36 h-36 flex items-center justify-center my-4">
            <svg className="w-full h-full transform -rotate-90">
              <circle
                cx="72"
                cy="72"
                r="56"
                className="stroke-surface-container"
                strokeWidth="8"
                fill="none"
              />
              <circle
                cx="72"
                cy="72"
                r="56"
                className="stroke-[#0b3d2e]"
                strokeWidth="8"
                fill="none"
                strokeDasharray={351.8}
                strokeDashoffset={351.8 * (1 - 0.88)}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute flex flex-col items-center">
              <span className="font-playfair text-3xl font-extrabold text-primary">88</span>
              <span className="text-[9px] text-on-surface-variant font-medium tracking-widest uppercase mt-0.5">
                Growth Score
              </span>
            </div>
          </div>

          <div className="w-full grid grid-cols-2 gap-3 mt-2">
            <div className="bg-surface-container-low border border-outline-variant/10 rounded-2xl p-3 text-center">
              <span className="text-[9px] text-on-surface-variant/80 font-medium tracking-wider uppercase block">Sentiment</span>
              <span className="font-playfair text-sm font-bold text-primary mt-0.5 block">High</span>
            </div>
            <div className="bg-surface-container-low border border-outline-variant/10 rounded-2xl p-3 text-center">
              <span className="text-[9px] text-on-surface-variant/80 font-medium tracking-wider uppercase block">Loyalty</span>
              <span className="font-playfair text-sm font-bold text-primary mt-0.5 block">A+</span>
            </div>
          </div>
        </div>
      </div>

      {/* Row of Statistics Cards */}
      <div className="grid sm:grid-cols-3 gap-6">
        {stats.map((stat, idx) => {
          const Icon = stat.icon;
          return (
            <div 
              key={idx} 
              className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-2xl p-6 shadow-sm flex items-center gap-4 hover:shadow-md transition-shadow"
            >
              <div className="w-12 h-12 rounded-xl bg-surface-container flex items-center justify-center border border-outline-variant/20 flex-shrink-0">
                <Icon className="w-5 h-5 text-primary" />
              </div>
              <div className="flex flex-col">
                <span className="text-[10px] text-on-surface-variant font-medium uppercase tracking-wider">
                  {stat.label}
                </span>
                <span className="font-playfair text-2xl font-extrabold text-primary leading-tight mt-0.5">
                  {stat.value}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Bottom Recommended Actions */}
      <div className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-3xl p-8 shadow-sm flex flex-col gap-6 hover:shadow-md transition-shadow">
        <div className="flex items-center justify-between border-b border-outline-variant/20 pb-4">
          <h3 className="font-playfair text-lg font-bold text-primary">Recommended Actions</h3>
          <Link href="/dashboard/insights" className="text-xs font-semibold font-literata text-[#735c00] hover:underline">
            View All Intelligence
          </Link>
        </div>

        <div className="flex flex-col gap-5">
          {actions.map((action) => {
            const Icon = action.icon;
            return (
              <div 
                key={action.id} 
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 hover:bg-surface-container/30 rounded-2xl transition-colors duration-150 group border border-transparent hover:border-outline-variant/10"
              >
                <div className="flex gap-4 items-start">
                  <div className={`p-3 rounded-xl ${action.iconBg} flex-shrink-0 mt-0.5`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div className="flex flex-col gap-1">
                    <h4 className="font-playfair text-base font-bold text-primary">
                      {action.title}
                    </h4>
                    <p className="text-xs text-on-surface-variant font-literata leading-relaxed max-w-xl">
                      {action.description}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3 self-end sm:self-center">
                  <button className="px-4 py-2 border border-outline-variant/30 text-xs font-semibold font-literata rounded-xl text-primary hover:bg-surface-container transition-all cursor-pointer whitespace-nowrap">
                    {action.buttonText}
                  </button>
                  <button 
                    aria-label="Dismiss recommendation"
                    className="p-2 rounded-lg text-on-surface-variant/40 hover:text-error hover:bg-error-container/10 transition-all cursor-pointer"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </motion.div>
  );
}
