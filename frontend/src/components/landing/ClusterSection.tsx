"use client";

import { motion, useInView } from "framer-motion";
import { useRef } from "react";
import { CheckCircle2 } from "lucide-react";
import Image from "next/image";

const fadeUp = {
  hidden: { opacity: 0, y: 32 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.65, ease: [0.22, 1, 0.36, 1] },
  },
};

const topicNodes = [
  { label: "#Cinematography", x: "72%", y: "12%", size: "sm" },
  { label: "#Sustainability", x: "4%", y: "52%", size: "sm" },
  { label: "#WorkflowEfficiency", x: "14%", y: "80%", size: "sm" },
];

const features = [
  "Understand audience intent—not just keywords or sentiment.",
  "Make every content decision using real audience data instead of guesswork.",
  "Know the topics generating the most curiosity, confusion, and excitement.",
  "Identify emerging trends before they become obvious.",
];

export default function ClusterSection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <section
      id="methodology"
      ref={ref}
      className="py-24 lg:py-32 bg-surface-container-low/50"
    >
      <div className="max-w-[1280px] mx-auto px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-16 lg:gap-24 items-center">
          <div>
            <Image
              src="/images/voice.png"
              alt="Audience Clustering Visual"
              width={500}
              height={500}
              className="w-full h-full object-cover"
            />
          </div>

          {/* Right — copy */}
          <motion.div
            variants={fadeUp}
            initial="hidden"
            animate={inView ? "visible" : "hidden"}
            transition={{ delay: 0.15 }}
          >
            <h2 className="font-playfair text-[2rem] lg:text-[2.5rem] font-bold text-on-surface leading-[1.2] tracking-[-0.01em] mb-5">
              Your audience has already told you what they want.
            </h2>
            <p className="font-literata text-base text-on-surface-variant leading-[1.7] mb-8">
              Every comment is a signal. OluOra analyzes thousands of
              conversations to uncover the patterns, questions, and unmet needs
              that drive better content, stronger engagement, and faster channel
              growth.
            </p>
            <ul className="space-y-3.5">
              {features.map((feat, i) => (
                <motion.li
                  key={i}
                  initial={{ opacity: 0, x: -12 }}
                  animate={inView ? { opacity: 1, x: 0 } : {}}
                  transition={{ delay: 0.35 + i * 0.1 }}
                  className="flex items-start gap-3"
                >
                  <CheckCircle2 className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                  <span className="font-literata text-sm text-on-surface-variant leading-[1.6]">
                    {feat}
                  </span>
                </motion.li>
              ))}
            </ul>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
