"use client";

import { motion, useInView } from "framer-motion";
import { useRef } from "react";
import {
  Brain,
  Layers,
  MessageSquareQuote,
  Sparkles,
  TrendingUp,
  Users,
  Zap,
} from "lucide-react";

const fadeUp = {
  hidden: { opacity: 0, y: 28 },
  visible: (delay = 0) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.65, ease: [0.22, 1, 0.36, 1] as const, delay },
  }),
};

const stats = [
  { value: "10K+", label: "Comments analysed per sync" },
  { value: "94%", label: "Signal-to-noise improvement" },
  { value: "3 min", label: "Average time to first insight" },
];

export default function AboutSection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <section
      id="about"
      ref={ref}
      className="py-24 lg:py-32 bg-surface-container-low/50"
    >
      <div className="max-w-[1280px] mx-auto px-6 lg:px-8">
        {/* Section header */}
        <motion.div
          variants={fadeUp}
          initial="hidden"
          animate={inView ? "visible" : "hidden"}
          custom={0}
          className="mb-14"
        >
          <p className="font-literata text-xs font-semibold tracking-[0.12em] uppercase text-secondary mb-3">
            What We're Building
          </p>
          <h2 className="font-playfair text-[2rem] lg:text-[2.625rem] font-bold text-on-surface leading-[1.18] tracking-[-0.015em] max-w-[640px]">
            Your audience has already told you what they want.
          </h2>
        </motion.div>

        {/* Bento Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-4 auto-rows-auto">
          {/* Cell 1 — Wide mission statement (col-span 7) */}
          <motion.div
            variants={fadeUp}
            initial="hidden"
            animate={inView ? "visible" : "hidden"}
            custom={0.1}
            className="lg:col-span-7 card-base p-8 flex flex-col justify-between min-h-[220px]"
            style={{
              background:
                "linear-gradient(145deg, #0b3d2e 0%, #1a5240 80%, #214f3f 100%)",
            }}
          >
            <div>
              <div className="flex items-center gap-2 mb-5">
                <div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center">
                  <Brain className="w-4 h-4 text-secondary" />
                </div>
                <span className="font-literata text-xs text-white/60 uppercase tracking-[0.1em]">
                  The OluOra Intelligence Engine
                </span>
              </div>
              <p className="font-playfair text-xl text-white font-semibold leading-[1.4] mb-4">
                Every comment section is a goldmine of unfiltered audience
                feedback. We turn that noise into your competitive edge.
              </p>
              <p className="font-literata text-sm text-white/65 leading-[1.7]">
                OluOra connects to your YouTube / Tiktok / Instagram channels,
                analyses thousands of comments, and delivers structured content
                suggestions so you spend less time reading and more time
                creating.
              </p>
            </div>
          </motion.div>

          {/* Cell 2 — Stats stack (col-span 5) */}
          <motion.div
            variants={fadeUp}
            initial="hidden"
            animate={inView ? "visible" : "hidden"}
            custom={0.15}
            className="lg:col-span-5 card-base p-7 flex flex-col justify-center gap-6"
          >
            {stats.map((stat, i) => (
              <div
                key={i}
                className="flex items-center gap-4"
              >
                <span className="font-playfair text-3xl font-bold text-primary tabular-nums min-w-[72px]">
                  {stat.value}
                </span>
                <div className="h-px flex-1 bg-outline-variant/40" />
                <span className="font-literata text-sm text-on-surface-variant text-right max-w-[140px] leading-[1.5]">
                  {stat.label}
                </span>
              </div>
            ))}
          </motion.div>

          {/* Cell 3 — How it works (col-span 4) */}
          <motion.div
            variants={fadeUp}
            initial="hidden"
            animate={inView ? "visible" : "hidden"}
            custom={0.2}
            className="lg:col-span-4 card-base p-7"
          >
            <div className="flex items-center gap-2 mb-5">
              <div className="w-8 h-8 rounded-lg bg-primary/8 flex items-center justify-center">
                <Layers className="w-4 h-4 text-primary" />
              </div>
              <h3 className="font-playfair text-base font-semibold text-on-surface">
                How It Works
              </h3>
            </div>
            <ol className="space-y-3.5">
              {[
                {
                  step: "01",
                  text: "Connect your YouTube channel via Google OAuth.",
                },
                {
                  step: "02",
                  text: "OluOra syncs and cleans your comment data automatically.",
                },
                {
                  step: "03",
                  text: "AI clusters comments by theme, sentiment, and intent.",
                },
                {
                  step: "04",
                  text: "You receive actionable briefs and content recommendations.",
                },
              ].map(({ step, text }) => (
                <li
                  key={step}
                  className="flex items-start gap-3"
                >
                  <span className="font-literata text-xs font-semibold text-secondary min-w-[24px] mt-0.5">
                    {step}
                  </span>
                  <span className="font-literata text-sm text-on-surface-variant leading-[1.65]">
                    {text}
                  </span>
                </li>
              ))}
            </ol>
          </motion.div>

          {/* Cell 4 — Quote pull (col-span 4) */}
          <motion.div
            variants={fadeUp}
            initial="hidden"
            animate={inView ? "visible" : "hidden"}
            custom={0.25}
            className="lg:col-span-4 card-base p-7 flex flex-col justify-between"
            style={{
              background:
                "linear-gradient(145deg, rgba(115,92,0,0.05) 0%, transparent 70%)",
            }}
          >
            <div>
              <div className="flex items-center gap-1.5 mb-5">
                <span className="ai-badge flex items-center gap-1">
                  <Sparkles className="w-2.5 h-2.5" />
                  AI Insight
                </span>
              </div>
              <MessageSquareQuote className="w-6 h-6 text-secondary/50 mb-3" />
              <p className="font-literata text-base text-on-surface leading-[1.65] italic">
                &ldquo;94% of your audience is asking for a deep-dive on
                sustainable architecture. A topic you haven&apos;t covered
                yet.&rdquo;
              </p>
            </div>
            <p className="font-literata text-xs text-on-surface-variant/60 mt-5">
              Example insight generated from 3,400 comments across 12 videos.
            </p>
          </motion.div>

          {/* Cell 5 — Who it's for (col-span 4) */}
          <motion.div
            variants={fadeUp}
            initial="hidden"
            animate={inView ? "visible" : "hidden"}
            custom={0.3}
            className="lg:col-span-4 card-base p-7"
          >
            <div className="flex items-center gap-2 mb-5">
              <div className="w-8 h-8 rounded-lg bg-primary/8 flex items-center justify-center">
                <Users className="w-4 h-4 text-primary" />
              </div>
              <h3 className="font-playfair text-base font-semibold text-on-surface">
                Built For
              </h3>
            </div>
            <ul className="space-y-3">
              {[
                {
                  title: "Educators & Tutors",
                  desc: "Know which concepts confuse your audience most.",
                },
                {
                  title: "Lifestyle Creators",
                  desc: "Spot the content pillars your community loves deeply.",
                },
                {
                  title: "Finance & Tech Creators",
                  desc: "Surface the questions your audience can't stop asking.",
                },
                {
                  title: "Media Studios",
                  desc: "Scale audience intelligence across an entire channel portfolio.",
                },
              ].map(({ title, desc }) => (
                <li
                  key={title}
                  className="flex items-start gap-2.5"
                >
                  <div className="w-1.5 h-1.5 rounded-full bg-primary mt-2 flex-shrink-0" />
                  <div>
                    <p className="font-literata text-sm font-semibold text-on-surface">
                      {title}
                    </p>
                    <p className="font-literata text-xs text-on-surface-variant leading-[1.55] mt-0.5">
                      {desc}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          </motion.div>

          {/* Cell 6 — Speed badge (col-span 5) */}
          <motion.div
            variants={fadeUp}
            initial="hidden"
            animate={inView ? "visible" : "hidden"}
            custom={0.35}
            className="lg:col-span-5 card-base p-7 flex flex-col justify-between min-h-[180px]"
          >
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-primary/8 flex items-center justify-center">
                <Zap className="w-4 h-4 text-primary" />
              </div>
              <h3 className="font-playfair text-base font-semibold text-on-surface">
                Privacy & Data Principles
              </h3>
            </div>
            <p className="font-literata text-sm text-on-surface-variant leading-[1.7]">
              OluOra reads only publicly available comment data from your
              channel. We never store private viewer information, never share
              data with third parties, and give you full control over your
              channel connection at any time.
            </p>
          </motion.div>

          {/* Cell 7 — Trend card (col-span 7) */}
          <motion.div
            variants={fadeUp}
            initial="hidden"
            animate={inView ? "visible" : "hidden"}
            custom={0.4}
            className="lg:col-span-7 card-base p-0 overflow-hidden"
          >
            {/* Mini trend visual */}
            <div
              className="h-28 px-6 flex items-end gap-1.5 pb-4"
              style={{
                background: "linear-gradient(135deg, #1f211f 0%, #2c302b 100%)",
              }}
            >
              {[30, 45, 38, 55, 48, 66, 72, 60, 80, 88, 76, 95].map((h, i) => (
                <div
                  key={i}
                  className="flex-1 rounded-sm transition-all"
                  style={{
                    height: `${h}%`,
                    background:
                      i >= 9
                        ? "rgba(233, 195, 73, 0.85)"
                        : "rgba(255,255,255,0.15)",
                  }}
                />
              ))}
            </div>
            <div className="p-6 flex items-start gap-4">
              <div className="w-9 h-9 rounded-xl bg-primary/8 flex items-center justify-center flex-shrink-0">
                <TrendingUp className="w-4.5 h-4.5 text-primary" />
              </div>
              <div>
                <h3 className="font-playfair text-base font-semibold text-on-surface mb-1.5">
                  Trend Detection Before It Peaks
                </h3>
                <p className="font-literata text-sm text-on-surface-variant leading-[1.65]">
                  OluOra tracks rising topics in your comment section week over
                  week. When a conversation theme starts accelerating, you're
                  the first to know so you can publish before it's mainstream.
                </p>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
