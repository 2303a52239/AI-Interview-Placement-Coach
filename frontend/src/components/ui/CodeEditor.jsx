import { useEffect, useState } from "react";
import Editor, { loader } from "@monaco-editor/react";
import { useTheme } from "../../context/ThemeContext";

const MONACO_LANG = { python: "python", java: "java", cpp: "cpp" };

/**
 * Code editor for Python, Java and C++.
 *
 * Uses Monaco (the VS Code editor) when it can load. Monaco is fetched from a CDN at
 * runtime, so on an offline machine or a restricted network it never arrives; after a
 * short wait we switch to a plain monospace textarea so the coding module stays usable.
 */
export default function CodeEditor({ value, onChange, height = "420px", language = "java" }) {
  const [monacoReady, setMonacoReady] = useState(false);
  const [useFallback, setUseFallback] = useState(false);
  const { theme } = useTheme();

  // If the CDN script can't be fetched, switch to the textarea straight away instead of waiting.
  useEffect(() => {
    loader.init().catch(() => setUseFallback(true));
    // The Monaco loader rejects with a bare DOM Event when its script can't be fetched; we handle that
    // by falling back to the textarea, so don't let it surface as an uncaught error.
    const swallow = (e) => { if (e.reason instanceof Event) e.preventDefault(); };
    window.addEventListener("unhandledrejection", swallow);
    return () => window.removeEventListener("unhandledrejection", swallow);
  }, []);

  useEffect(() => {
    if (monacoReady) return undefined;
    const timer = setTimeout(() => setUseFallback(true), 6000);
    return () => clearTimeout(timer);
  }, [monacoReady]);

  if (useFallback && !monacoReady) {
    const handleKeyDown = (e) => {
      if (e.key !== "Tab") return;
      e.preventDefault();
      const { selectionStart, selectionEnd } = e.target;
      onChange(value.slice(0, selectionStart) + "    " + value.slice(selectionEnd));
      requestAnimationFrame(() => { e.target.selectionStart = e.target.selectionEnd = selectionStart + 4; });
    };
    return (
      <div>
        <p className="bg-amber-light px-4 py-2 text-xs text-amber-dark">
          Basic editor: the full code editor couldn't load (it needs an internet connection). Everything else works the same.
        </p>
        <textarea
          aria-label="Source code" value={value} onChange={(e) => onChange(e.target.value)} onKeyDown={handleKeyDown}
          spellCheck={false} style={{ height }}
          className="w-full resize-none bg-[#1e1e1e] p-4 font-mono text-[13px] leading-relaxed text-[#d4d4d4] outline-none"
        />
      </div>
    );
  }

  return (
    <Editor
      height={height} language={MONACO_LANG[language] || "plaintext"} value={value} path={`solution.${language}`}
      onChange={(v) => onChange(v ?? "")} onMount={() => setMonacoReady(true)}
      theme={theme === "dark" ? "vs-dark" : "vs-dark"}
      options={{ fontSize: 13, minimap: { enabled: false }, fontFamily: "IBM Plex Mono, monospace", scrollBeyondLastLine: false }}
    />
  );
}
