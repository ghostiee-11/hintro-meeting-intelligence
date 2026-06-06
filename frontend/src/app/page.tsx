"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Bell,
  BrainCircuit,
  ListChecks,
  Quote,
  Search,
  ShieldCheck,
} from "lucide-react";
import { Logo } from "@/components/logo";
import { SplineScene } from "@/components/ui/splite";
import { Spotlight } from "@/components/ui/spotlight";
import { LiquidButton } from "@/components/ui/liquid-glass-button";
import { LampContainer } from "@/components/ui/lamp";
import { ThemeToggle } from "@/components/theme-toggle";

const features = [
  {
    icon: ShieldCheck,
    title: "Verifiable citations",
    desc: "Every AI insight is mechanically checked against the transcript. Hallucinated citations are dropped before they ever reach you.",
  },
  {
    icon: BrainCircuit,
    title: "Resilient analysis",
    desc: "Gemini powers analysis with an automatic Groq fallback, so the service keeps working during provider outages.",
  },
  {
    icon: ListChecks,
    title: "Action tracking",
    desc: "Extracted action items become a live board with assignees, due dates, and overdue detection.",
  },
  {
    icon: Bell,
    title: "Two-way reminders",
    desc: "Overdue items trigger Telegram and Discord reminders. Mark them done straight from the chat.",
  },
  {
    icon: Search,
    title: "Semantic search",
    desc: "Ask questions across every meeting. pgvector embeddings find the moment you mean, not just the words.",
  },
  {
    icon: Quote,
    title: "Grounding scores",
    desc: "Each insight shows a confidence score from citation coverage and lexical overlap, so trust is measurable.",
  },
];

export default function Landing() {
  return (
    <div className="min-h-dvh bg-black text-white">
      {/* Nav */}
      <header className="absolute inset-x-0 top-0 z-30 mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <Logo wordClassName="text-white" />
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Link href="/login" className="rounded-md px-3 py-2 text-sm text-neutral-300 hover:text-white">
            Sign in
          </Link>
          <Link href="/register">
            <LiquidButton size="default" className="text-white">
              Get started
            </LiquidButton>
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="relative h-dvh w-full overflow-hidden bg-black/[0.96] antialiased">
        <Spotlight className="-top-40 left-0 md:-top-20 md:left-60" fill="white" />
        <div className="mx-auto grid h-full max-w-6xl grid-cols-1 items-center gap-4 px-6 md:grid-cols-2">
          <div className="relative z-10 flex flex-col justify-center">
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="mb-5 inline-flex w-fit items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-neutral-300"
            >
              <ShieldCheck className="size-3.5 text-emerald-400" />
              Grounded AI that refuses to hallucinate
            </motion.div>
            <h1 className="bg-linear-to-b from-neutral-50 to-neutral-400 bg-clip-text text-5xl font-bold leading-tight tracking-tight text-transparent sm:text-6xl">
              Meeting intelligence you can trust
            </h1>
            <p className="mt-6 max-w-lg text-lg text-neutral-300">
              Hintro turns transcripts into summaries, decisions, action items, and follow-ups, with
              a verifiable citation for every claim. It tracks who owes what and nudges people through
              Telegram and Discord.
            </p>
            <div className="mt-9 flex flex-wrap items-center gap-3">
              <Link href="/register">
                <LiquidButton size="xl" className="text-white">
                  Start free <ArrowRight className="size-4" />
                </LiquidButton>
              </Link>
              <Link
                href="/login"
                className="rounded-md border border-white/15 px-6 py-3 text-sm font-medium text-neutral-200 transition-colors hover:bg-white/5"
              >
                Live demo
              </Link>
            </div>
            <p className="mt-4 text-xs text-neutral-500">
              Demo login: demo@hintro.ai / demo-password-123
            </p>
          </div>

          <div className="relative hidden h-full md:block">
            <SplineScene
              scene="https://prod.spline.design/kZDDjO5HuC9GJUM2/scene.splinecode"
              className="h-full w-full"
            />
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-6xl px-6 py-24">
        <div className="mb-12 text-center">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Engineered to be believed
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-neutral-400">
            Not a wrapper around a prompt. A grounding pipeline, a resilient model layer, and real
            integrations.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.45, delay: i * 0.05 }}
              className="group rounded-xl border border-white/10 bg-white/[0.03] p-6 transition-all hover:-translate-y-1 hover:border-white/20 hover:bg-white/[0.06]"
            >
              <div className="mb-4 grid size-11 place-items-center rounded-lg bg-primary/20 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                <f.icon className="size-5" />
              </div>
              <h3 className="font-semibold">{f.title}</h3>
              <p className="mt-2 text-sm text-neutral-400">{f.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Lamp CTA */}
      <LampContainer className="min-h-[36rem]">
        <motion.h2
          initial={{ opacity: 0.5, y: 100 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.8, ease: "easeInOut" }}
          className="bg-linear-to-br from-neutral-100 to-neutral-400 bg-clip-text py-4 text-center text-4xl font-semibold tracking-tight text-transparent md:text-6xl"
        >
          Grounded by design
        </motion.h2>
        <p className="mx-auto mt-2 max-w-md text-center text-neutral-400">
          See the citation engine refuse to hallucinate on a real transcript.
        </p>
        <Link href="/register" className="mt-8">
          <LiquidButton size="xl" className="text-white">
            Try it now <ArrowRight className="size-4" />
          </LiquidButton>
        </Link>
      </LampContainer>

      <footer className="border-t border-white/10 py-8 text-center text-sm text-neutral-500">
        Built for the Hintro Backend / Fullstack assignment. FastAPI, Next.js, PostgreSQL + pgvector.
      </footer>
    </div>
  );
}
