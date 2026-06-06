"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { Button } from "./ui/button";
import { Input, Label } from "./ui/input";
import { PasswordInput } from "./ui/password-input";
import { Typewriter } from "./ui/typewriter";
import { Logo } from "./logo";
import { useAuth } from "@/lib/auth";
import { ApiClientError } from "@/lib/api";

const QUOTES = [
  "Every insight, cited.",
  "Meetings you can actually trust.",
  "No hallucinations. Just the transcript.",
  "Decisions, action items, follow-ups, grounded.",
];

const HIGHLIGHTS = [
  "Grounded AI with verifiable citations",
  "Action tracking and overdue reminders",
  "Semantic search across every meeting",
];

export function AuthScreen({ mode: initialMode }: { mode: "login" | "register" }) {
  const [isSignIn, setIsSignIn] = useState(initialMode === "login");
  const { login, register } = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setLoading(true);
    try {
      if (isSignIn) {
        await login(String(form.get("email")), String(form.get("password")));
      } else {
        await register(
          String(form.get("email")),
          String(form.get("name")),
          String(form.get("password")),
        );
      }
      toast.success(isSignIn ? "Welcome back" : "Account created");
      router.push("/dashboard");
    } catch (err) {
      toast.error(err instanceof ApiClientError ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-dvh w-full md:grid md:grid-cols-2">
      {/* Form side */}
      <div className="flex min-h-dvh items-center justify-center p-6 md:min-h-0 md:py-12">
        <div className="mx-auto grid w-[350px] gap-6">
          <Link href="/" className="mx-auto md:hidden">
            <Logo />
          </Link>
          <div className="flex flex-col items-center gap-2 text-center">
            <h1 className="text-2xl font-bold">
              {isSignIn ? "Sign in to your account" : "Create your account"}
            </h1>
            <p className="text-balance text-sm text-muted-foreground">
              {isSignIn
                ? "Enter your email below to sign in"
                : "Enter your details below to get started"}
            </p>
          </div>

          <form onSubmit={onSubmit} autoComplete="on" className="grid gap-4">
            {!isSignIn && (
              <div className="grid gap-1.5">
                <Label htmlFor="name">Full name</Label>
                <Input id="name" name="name" type="text" placeholder="Aman Kumar" required minLength={2} autoComplete="name" />
              </div>
            )}
            <div className="grid gap-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                name="email"
                type="email"
                placeholder="you@example.com"
                required
                autoComplete="email"
                defaultValue={isSignIn ? "demo@hintro.ai" : ""}
              />
            </div>
            <PasswordInput
              name="password"
              label="Password"
              required
              minLength={8}
              placeholder="Password"
              autoComplete={isSignIn ? "current-password" : "new-password"}
              defaultValue={isSignIn ? "demo-password-123" : ""}
            />
            <Button type="submit" className="mt-2" disabled={loading}>
              {loading ? "Please wait..." : isSignIn ? "Sign in" : "Create account"}
            </Button>
          </form>

          <div className="text-center text-sm text-muted-foreground">
            {isSignIn ? "Don't have an account?" : "Already have an account?"}{" "}
            <button
              type="button"
              onClick={() => setIsSignIn((v) => !v)}
              className="font-medium text-foreground underline-offset-4 hover:underline"
            >
              {isSignIn ? "Sign up" : "Sign in"}
            </button>
          </div>

          {isSignIn && (
            <p className="text-center text-xs text-muted-foreground">
              Demo: demo@hintro.ai / demo-password-123
            </p>
          )}
        </div>
      </div>

      {/* Brand side */}
      <div className="relative hidden overflow-hidden bg-slate-950 md:block">
        <div className="aurora pointer-events-none absolute inset-0" />
        <div className="relative z-10 flex h-full flex-col justify-between p-10 text-white">
          <Link href="/" className="text-white">
            <Logo wordClassName="text-white" />
          </Link>
          <div className="space-y-6">
            <blockquote className="text-3xl font-semibold leading-tight tracking-tight">
              &ldquo;
              <Typewriter text={QUOTES} speed={55} deleteSpeed={30} delay={1800} loop className="text-white" />
              &rdquo;
            </blockquote>
            <ul className="space-y-3">
              {HIGHLIGHTS.map((h) => (
                <li key={h} className="flex items-center gap-2 text-sm text-neutral-300">
                  <ShieldCheck className="size-4 text-emerald-400" />
                  {h}
                </li>
              ))}
            </ul>
          </div>
          <p className="text-xs text-neutral-500">
            Hintro Meeting Intelligence. FastAPI, Next.js, PostgreSQL + pgvector.
          </p>
        </div>
      </div>
    </div>
  );
}
