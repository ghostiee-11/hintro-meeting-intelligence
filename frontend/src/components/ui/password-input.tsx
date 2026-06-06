"use client";

import * as React from "react";
import { useId, useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { cn } from "@/lib/utils";
import { Input, Label } from "./input";

export interface PasswordInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export const PasswordInput = React.forwardRef<HTMLInputElement, PasswordInputProps>(
  ({ className, label, ...props }, ref) => {
    const id = useId();
    const [show, setShow] = useState(false);
    return (
      <div className="grid w-full items-center gap-1.5">
        {label && <Label htmlFor={id}>{label}</Label>}
        <div className="relative">
          <Input
            id={id}
            type={show ? "text" : "password"}
            className={cn("pe-10", className)}
            ref={ref}
            {...props}
          />
          <button
            type="button"
            onClick={() => setShow((v) => !v)}
            className="absolute inset-y-0 end-0 flex w-10 items-center justify-center text-muted-foreground transition-colors hover:text-foreground"
            aria-label={show ? "Hide password" : "Show password"}
          >
            {show ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
          </button>
        </div>
      </div>
    );
  },
);
PasswordInput.displayName = "PasswordInput";
