"use client";

import { ThemeProvider } from "next-themes";
import { Toaster } from "sonner";
import { AuthProvider } from "@/lib/auth";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
      <AuthProvider>
        {children}
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: "var(--card)",
              color: "var(--foreground)",
              border: "1px solid var(--border)",
            },
          }}
        />
      </AuthProvider>
    </ThemeProvider>
  );
}
