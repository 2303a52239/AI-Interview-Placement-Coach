import * as React from "react";
import { cn } from "@/lib/utils";

const field = "w-full rounded-card border border-paper-line bg-paper-panel px-3 text-sm text-ink placeholder:text-ink-faint focus-ring outline-none disabled:opacity-60";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(({ className, type = "text", ...p }, ref) => (
  <input ref={ref} type={type} className={cn(field, "h-10", className)} {...p} />
));
Input.displayName = "Input";

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(({ className, ...p }, ref) => (
  <textarea ref={ref} className={cn(field, "min-h-[80px] py-2", className)} {...p} />
));
Textarea.displayName = "Textarea";

export const Select = React.forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(({ className, ...p }, ref) => (
  <select ref={ref} className={cn(field, "h-10", className)} {...p} />
));
Select.displayName = "Select";

export const Label = ({ className, ...p }: React.LabelHTMLAttributes<HTMLLabelElement>) => (
  <label className={cn("mb-1 block text-sm font-medium", className)} {...p} />
);
