"use client";

import { motion, useInView } from "framer-motion";
import { useRef } from "react";
import { BarChart3, FileText, TrendingUp, Globe } from "lucide-react";

const features = [
  {
    icon: BarChart3,
    title: "Sentiment Resonance Map",
    description:
      "Visualise the emotional pulse of your community across every video in your library.",
    size: "large",
    accent: false,
  },
  {
    icon: FileText,
    title: "Script-Ready Briefs",
    description:
      "AI-generated content suggestions based on audience demand patterns.",
    size: "small",
    accent: true,
  },
  {
    icon: TrendingUp,
    title: "Trend Prediction",
    description:
      "Identify rising topics before they peak to stay ahead of the content curve.",
    size: "small",
    accent: false,
  },
  {
    icon: Globe,
    title: "Competitive Intelligence",
    description:
      "Benchmark your audience engagement metrics against the leaders in your niche.",
    size: "small",
    accent: false,
  },
];

export default function FeaturesSection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <section
      id="solutions"
      ref={ref}
      className="py-24 lg:py-32"
    >
      <div className="max-w-[1280px] mx-auto px-6 lg:px-8">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <p className="font-literata text-xs font-semibold tracking-[0.12em] uppercase text-secondary mb-3">
            Creator Intelligence Engine
          </p>
          <h2 className="font-playfair text-[2.25rem] lg:text-[2.875rem] font-bold text-on-surface leading-[1.15] tracking-[-0.015em]">
            Everything you need to understand your audience, uncover
            opportunities, and create with confidence.
          </h2>
        </motion.div>

        {/* Feature grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {/* Large card — Sentiment Map */}
          <motion.div
            initial={{ opacity: 0, y: 32 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="lg:col-span-2 card-base p-0 overflow-hidden group cursor-default"
          >
            {/* Preview area */}
            <div
              className="h-48 relative overflow-hidden"
              style={{
                background:
                  "linear-gradient(135deg, #0b3d2e 0%, #214f3f 60%, #396756 100%)",
              }}
            >
              {/* Mini dashboard mockup */}
              <div className="absolute inset-4 rounded-lg bg-white/8 backdrop-blur-sm border border-white/10 p-3">
                <div className="flex items-center gap-1.5 mb-3">
                  <div className="w-2 h-2 rounded-full bg-secondary/80" />
                  <span className="font-literata text-xs text-white/60">
                    Audience Intelligence Overview
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {[65, 82, 48, 91, 37, 74].map((h, i) => (
                    <div
                      key={i}
                      className="rounded-sm bg-white/15"
                      style={{ height: `${h * 0.4}px` }}
                    />
                  ))}
                </div>
                <div className="mt-3 flex items-center justify-between">
                  <span className="font-literata text-xs text-white/50">
                    14.2k comments
                  </span>
                  <span className="font-literata text-xs text-secondary-container font-medium">
                    +8.5%
                  </span>
                </div>
              </div>
            </div>
            <div className="p-6">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-9 h-9 rounded-xl bg-primary/8 flex items-center justify-center">
                  <BarChart3 className="w-4.5 h-4.5 text-primary" />
                </div>
                <h3 className="font-playfair text-lg font-semibold text-on-surface">
                  Sentiment Resonance Map
                </h3>
              </div>
              <p className="font-literata text-sm text-on-surface-variant leading-[1.65]">
                See how your audience feels, reacts, and responds across every
                video—revealing patterns that ordinary analytics can't uncover.
              </p>
            </div>
          </motion.div>

          {/* Script-Ready Briefs — gold accent */}
          <motion.div
            initial={{ opacity: 0, y: 32 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.15 }}
            className="card-base p-6 group cursor-default"
            style={{
              background:
                "linear-gradient(145deg, rgba(115,92,0,0.04) 0%, transparent 60%)",
            }}
          >
            <div className="flex items-center gap-2 mb-4">
              <span className="ai-badge flex items-center gap-1">
                <svg
                  className="w-2.5 h-2.5"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path d="M12 2L13.9 8.26L20.5 8.26L15.3 12.14L17.18 18.4L12 14.52L6.82 18.4L8.7 12.14L3.5 8.26L10.1 8.26L12 2Z" />
                </svg>
                AI Powered
              </span>
            </div>
            <div className="w-10 h-10 rounded-xl bg-secondary/10 flex items-center justify-center mb-4">
              <FileText className="w-5 h-5 text-secondary" />
            </div>
            <h3 className="font-playfair text-lg font-semibold text-on-surface mb-2">
              Script-Ready Briefs
            </h3>
            <p className="font-literata text-sm text-on-surface-variant leading-[1.65]">
              Turn thousands of audience conversations into structured content
              briefs your team can act on immediately.
            </p>
            <div className="mt-4 pt-4 border-t border-outline-variant/30">
              <button className="font-literata text-xs font-medium text-primary hover:text-primary-container flex items-center gap-1 transition-colors">
                Learn more →
              </button>
            </div>
          </motion.div>

          {/* Trend Prediction */}
          <motion.div
            initial={{ opacity: 0, y: 32 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="card-base p-6 group cursor-default"
          >
            <div className="w-10 h-10 rounded-xl bg-primary/8 flex items-center justify-center mb-4">
              <TrendingUp className="w-5 h-5 text-primary" />
            </div>
            <h3 className="font-playfair text-lg font-semibold text-on-surface mb-2">
              Trend Forecasting
            </h3>
            <p className="font-literata text-sm text-on-surface-variant leading-[1.65]">
              Detect emerging conversations before they become mainstream,
              giving you a first-mover advantage.
            </p>
          </motion.div>

          {/* Competitive Intelligence */}
          <motion.div
            initial={{ opacity: 0, y: 32 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.25 }}
            className="card-base p-0 overflow-hidden group cursor-default"
          >
            {/* Visual */}
            <div
              className="h-36 relative"
              style={{
                background: "linear-gradient(135deg, #1f211f 0%, #353634 100%)",
              }}
            >
              <div className="absolute inset-4 flex items-end gap-1.5">
                {[40, 65, 35, 80, 55, 90, 70].map((h, i) => (
                  <div
                    key={i}
                    className="flex-1 rounded-sm opacity-60"
                    style={{
                      height: `${h}%`,
                      background: i === 5 ? "#e9c349" : "rgba(255,255,255,0.2)",
                    }}
                  />
                ))}
              </div>
            </div>
            <div className="p-5">
              <div className="w-9 h-9 rounded-xl bg-primary/8 flex items-center justify-center mb-3">
                <Globe className="w-4.5 h-4.5 text-primary" />
              </div>
              <h3 className="font-playfair text-base font-semibold text-on-surface mb-1.5">
                Competitive Intelligence
              </h3>
              <p className="font-literata text-sm text-on-surface-variant leading-[1.6]">
                Understand how your audience engagement compares with leading
                creators and uncover opportunities to outperform your niche.
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
