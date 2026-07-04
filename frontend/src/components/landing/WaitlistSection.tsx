"use client";

import { useState, useRef } from "react";
import { motion, useInView } from "framer-motion";
import { ArrowRight, CheckCircle2, Loader2 } from "lucide-react";

type State = "idle" | "loading" | "success" | "error" | "duplicate";

export default function WaitlistSection() {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<State>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;

    setState("loading");
    setErrorMsg("");

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/waitlist`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: email.trim() }),
        },
      );

      if (res.ok) {
        setState("success");
        setEmail("");
        return;
      }

      const data = await res.json().catch(() => ({}));
      if (res.status === 409) {
        setState("duplicate");
        setErrorMsg("This email is already on the waitlist.");
      } else if (res.status === 422) {
        setState("error");
        setErrorMsg("Please enter a valid email address.");
      } else {
        setState("error");
        setErrorMsg(
          data?.error?.message ?? "Something went wrong. Please try again.",
        );
      }
    } catch {
      setState("error");
      setErrorMsg(
        "Unable to connect. Please check your connection and try again.",
      );
    }
  }

  return (
    <section
      id="waitlist"
      ref={ref}
      className="py-20 lg:py-28"
    >
      <div className="max-w-[1280px] mx-auto px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] as const }}
          className="relative rounded-3xl overflow-hidden px-8 py-16 lg:px-16 text-center"
          style={{
            background:
              "linear-gradient(160deg, #00261b 0%, #0b3d2e 50%, #214f3f 100%)",
          }}
        >
          {/* Subtle texture */}
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              backgroundImage:
                "radial-gradient(ellipse 60% 50% at 30% 60%, rgba(160,209,188,0.08) 0%, transparent 70%), radial-gradient(ellipse 40% 40% at 80% 30%, rgba(254,214,91,0.05) 0%, transparent 60%)",
            }}
          />

          <div className="relative z-10 max-w-[520px] mx-auto">
            <p className="font-literata text-xs font-semibold tracking-[0.12em] uppercase text-secondary-container mb-4">
              Early Access
            </p>
            <h2 className="font-playfair text-[1.875rem] lg:text-[2.25rem] font-bold text-white leading-[1.2] tracking-[-0.015em] mb-3">
              Elevate your creative intelligence.
            </h2>
            <p className="font-literata text-sm text-white/70 leading-[1.7] mb-8">
              Transform audience conversations into your next content strategy.
              Join the OluOra waitlist today.
            </p>

            {state === "success" ? (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex flex-col items-center gap-3"
              >
                <div className="w-14 h-14 rounded-full bg-secondary-container/20 flex items-center justify-center">
                  <CheckCircle2 className="w-7 h-7 text-secondary-container" />
                </div>
                <p className="font-playfair text-xl font-semibold text-white">
                  You&apos;re on the list!
                </p>
                <p className="font-literata text-sm text-white/60">
                  We&apos;ll be in touch as soon as your invite is ready.
                </p>
              </motion.div>
            ) : (
              <form
                onSubmit={handleSubmit}
                className="flex flex-col sm:flex-row gap-3"
                noValidate
              >
                <input
                  id="waitlist-email-input"
                  type="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (state !== "idle") setState("idle");
                  }}
                  placeholder="your@email.com"
                  required
                  disabled={state === "loading"}
                  className="flex-1 min-w-0 bg-white/10 border border-white/20 text-white placeholder:text-white/40 font-literata text-sm px-5 py-3.5 rounded-full focus:outline-none focus:border-secondary-container/70 focus:bg-white/15 transition-all disabled:opacity-60"
                  aria-label="Email address"
                />
                <button
                  id="waitlist-submit-btn"
                  type="submit"
                  disabled={state === "loading" || !email.trim()}
                  className="flex-shrink-0 inline-flex items-center justify-center gap-2 bg-secondary text-on-secondary font-literata text-sm font-medium px-6 py-3.5 rounded-full hover:bg-secondary/90 disabled:opacity-60 disabled:cursor-not-allowed transition-all duration-200 hover:shadow-lg hover:shadow-secondary/20"
                >
                  {state === "loading" ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      Join Waitlist
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>
            )}

            {/* Error / duplicate messages */}
            {(state === "error" || state === "duplicate") && (
              <motion.p
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                className="font-literata text-xs mt-3 text-red-300"
              >
                {errorMsg}
              </motion.p>
            )}

            {state === "idle" && (
              <p className="font-literata text-xs text-white/40 mt-4">
                Invitation-only access · No spam, ever.
              </p>
            )}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
