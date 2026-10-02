"use client";

import { Code2 } from "lucide-react";
import { memo, useEffect, useId, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

let mermaidReady: Promise<typeof import("mermaid").default> | null = null;
function loadMermaid() {
  mermaidReady ??= import("mermaid").then((m) => {
    m.default.initialize({ startOnLoad: false, theme: "neutral", securityLevel: "strict", fontFamily: "inherit" });
    return m.default;
  });
  return mermaidReady;
}

function Mermaid({ code }: { code: string }) {
  const id = useId().replace(/[^a-zA-Z0-9]/g, "");
  const [svg, setSvg] = useState("");
  const [failed, setFailed] = useState(false);
  const [showSource, setShowSource] = useState(false);
  useEffect(() => {
    let cancelled = false;
    loadMermaid()
      .then((m) => m.render(`mmd-${id}`, code))
      .then(({ svg }) => !cancelled && setSvg(svg))
      .catch(() => !cancelled && setFailed(true));
    return () => { cancelled = true; };
  }, [code, id]);

  if (failed) return <pre className="text-xs"><code>{code}</code></pre>;
  return (
    <div className="not-prose my-3 rounded-xl border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-100 px-3 py-1.5">
        <span className="text-xs font-medium text-slate-500">Diagram</span>
        <button onClick={() => setShowSource((s) => !s)} className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800">
          <Code2 className="h-3.5 w-3.5" /> {showSource ? "Hide" : "Source"}
        </button>
      </div>
      {showSource ? (
        <pre className="overflow-x-auto bg-slate-900 p-3 text-xs text-slate-100"><code>{code}</code></pre>
      ) : svg ? (
        <div className="flex justify-center overflow-x-auto p-4 [&_svg]:max-w-full" dangerouslySetInnerHTML={{ __html: svg }} />
      ) : (
        <div className="h-32 animate-pulse bg-slate-50" />
      )}
    </div>
  );
}

export const Markdown = memo(function Markdown({ content }: { content: string }) {
  return (
    <div className="prose prose-slate max-w-none text-[15px] leading-relaxed prose-headings:font-semibold prose-headings:text-slate-900 prose-h2:text-lg prose-h3:text-base prose-p:my-2 prose-li:my-0.5 prose-table:my-3 prose-th:bg-slate-50 prose-th:px-3 prose-th:py-1.5 prose-td:px-3 prose-td:py-1.5 prose-a:text-blue-600">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className, children, ...props }) {
            const lang = /language-(\w+)/.exec(className ?? "")?.[1];
            if (lang === "mermaid") return <Mermaid code={String(children).trim()} />;
            return <code className={className} {...props}>{children}</code>;
          },
          pre({ children }) {
            // Mermaid blocks render their own container; avoid wrapping them in <pre>.
            const child = Array.isArray(children) ? children[0] : children;
            if (child && typeof child === "object" && "props" in child && /language-mermaid/.test((child.props as { className?: string }).className ?? "")) {
              return <>{children}</>;
            }
            return <pre>{children}</pre>;
          },
          table({ children }) {
            return <div className="not-prose my-3 overflow-x-auto rounded-xl border border-slate-200"><table className="w-full border-collapse text-left text-[13px] [&_td]:border-t [&_td]:border-slate-100 [&_td]:px-3 [&_td]:py-2 [&_th]:bg-slate-50 [&_th]:px-3 [&_th]:py-2 [&_th]:font-semibold [&_th]:text-slate-600">{children}</table></div>;
          },
          a({ children, href }) {
            return <a href={href} target="_blank" rel="noreferrer">{children}</a>;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
});
