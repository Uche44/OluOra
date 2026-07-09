"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import Link from "next/link";
import { Sparkles, ArrowRight } from "lucide-react";

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: (delay = 0) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] as const, delay },
  }),
};

export default function HeroSection() {
  return (
    <section className="relative min-h-screen flex items-center overflow-hidden pt-16">
      {/* Subtle background pattern */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse 80% 60% at 60% 40%, rgba(188, 237, 215, 0.18) 0%, transparent 70%), radial-gradient(ellipse 50% 40% at 10% 80%, rgba(254, 214, 91, 0.06) 0%, transparent 60%)",
        }}
      />

      <div className="max-w-[1280px] mx-auto px-6 lg:px-8 w-full py-20 lg:py-28">
        <div className="grid lg:grid-cols-[1fr_480px] gap-12 lg:gap-16 items-center">
          {/* Left — copy */}
          <div>
            {/* Eyebrow */}
            <motion.p
              variants={fadeUp}
              initial="hidden"
              animate="visible"
              custom={0}
              className="font-literata text-xs font-semibold tracking-[0.12em] uppercase text-secondary mb-6"
            >
              The Future of Content Strategy
            </motion.p>

            {/* Headline */}
            <motion.h1
              variants={fadeUp}
              initial="hidden"
              animate="visible"
              custom={0.1}
              className="font-playfair text-[2.75rem] sm:text-[3.25rem] lg:text-[3.75rem] font-bold text-on-surface leading-[1.08] tracking-[-0.02em] mb-6"
            >
              Know exactly what your{" "}
              <em className="not-italic text-primary">audience wants </em> -
              without reading thousands of comments.
            </motion.h1>

            {/* Subline */}
            <motion.p
              variants={fadeUp}
              initial="hidden"
              animate="visible"
              custom={0.2}
              className="font-literata text-[1.0625rem] text-on-surface-variant leading-[1.65] mb-8 max-w-[520px]"
            >
              OluOra distills the chaotic sea of creator-audience interaction
              into crystal-clear actionable insights.
              <br /> You provide the data, we provide the intelligence.
            </motion.p>

            {/* CTAs */}
            <motion.div
              variants={fadeUp}
              initial="hidden"
              animate="visible"
              custom={0.3}
              className="flex flex-wrap items-center gap-3"
            >
              <Link
                href="#waitlist"
                id="hero-request-invite"
                className="inline-flex items-center gap-2 bg-primary text-on-primary font-literata text-sm font-medium px-6 py-3.5 rounded-full hover:bg-primary-container transition-all duration-200 shadow-sm hover:shadow-lg hover:shadow-primary/10 hover:-translate-y-0.5"
              >
                Join Waitlist
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="#about"
                id="hero-view-methodology"
                className="inline-flex items-center gap-2 border border-outline-variant text-on-surface-variant font-literata text-sm font-medium px-6 py-3.5 rounded-full hover:border-outline hover:text-on-surface hover:bg-surface-container-low transition-all duration-200"
              >
                Request Demo
              </Link>
            </motion.div>
          </div>

          {/* Right — editorial image + floating insight card */}
          <motion.div
            initial={{ opacity: 0, x: 32 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1], delay: 0.2 }}
            className="relative"
          >
            {/* Main image frame */}
            <div className="relative rounded-2xl overflow-hidden shadow-2xl shadow-primary/10 aspect-[4/4.5]">
              <Image
                src="/images/hero.png"
                alt="OluOra creator studio"
                fill
                className="object-cover"
                priority
                sizes="(max-width: 768px) 100vw, 480px"
              />
            </div>

            {/* Floating AI insight card */}
            <motion.div
              initial={{ opacity: 0, y: 16, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{
                duration: 0.6,
                ease: [0.22, 1, 0.36, 1],
                delay: 0.55,
              }}
              className="absolute -bottom-5 -left-6 right-4 lg:-left-8 card-base p-4 max-w-[280px]"
            >
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-0.5">
                  <div className="ai-badge flex items-center gap-1">
                    <Sparkles className="w-2.5 h-2.5" />
                    Real-time Insight
                  </div>
                </div>
              </div>
              <p className="font-literata text-sm text-on-surface leading-[1.6] mt-2.5">
                &ldquo;94% of your viewers are asking for a deep-dive on
                sustainable architecture.&rdquo;
              </p>
              <div className="mt-2 flex items-center gap-2">
                <div className="h-1.5 flex-1 rounded-full bg-surface-container-high overflow-hidden">
                  <div
                    className="h-full rounded-full bg-secondary"
                    style={{ width: "94%" }}
                  />
                </div>
                <span className="font-literata text-xs font-semibold text-secondary">
                  94%
                </span>
              </div>
            </motion.div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
