import React, { useEffect, useMemo, useRef, useState } from "react";

interface Section {
  id: string;
  title: string;
  body: string;
  bullets?: string[];
}

interface ScopeData {
  meta: {
    year: number;
    version: string;
    title: string;
    template_name?: string;
    created_at?: string;
    placeholders_retained?: boolean;
  };
  sections: Section[];
}

type ChatMessage = { role: "user" | "assistant"; content: string };

type AgentCommand =
  | "help"
  | "commands"
  | "fill"
  | "autofill"
  | "load"
  | "submit"
  | "reset"
  | "cancel"
  | "yes"
  | "no"
  | "exit";

type LoadOption = { id: string; label: string };

interface AgentResponse {
  message: string;
  draft: ScopeData | null;
  next_question?: string | null;
  saved_version?: string | null;
  load_options?: LoadOption[] | null;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const YEAR = 2026;

/**
 * Split text into normal + placeholder tokens.
 * Placeholder pattern: [ ... ]
 */
function renderWithPlaceholders(text: string) {
  const parts = text.split(/(\[[^\]]+\])/g);

  return parts.map((part, idx) => {
    const isPlaceholder = /^\[[^\]]+\]$/.test(part);
    if (!isPlaceholder) return <React.Fragment key={idx}>{part}</React.Fragment>;

    return (
      <span key={idx} className="text-rose-300 font-semibold">
        {part}
      </span>
    );
  });
}

export default function ScopeContext() {
  const [data, setData] = useState<ScopeData | null>(null);
  const [err, setErr] = useState<string | null>(null);

  // Agent / chat state
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
          "I’m in command mode.\n" +
          "Use: /help, /commands, /fill, /autofill, /load, /submit, /reset, /cancel\n" +
          "Confirmations: /yes, /no\n" +
          "Conversation mode: /exit\n\n" +
          "Tip: Type /commands to see the full list.",
    },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [fillQuestion, setFillQuestion] = useState<string | null>(null);
  const [loadOptions, setLoadOptions] = useState<LoadOption[] | null>(null);

  const chatBottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending, loadOptions]);

  // Initial load: get current scope JSON
  useEffect(() => {
    (async () => {
      try {
        setErr(null);
        const res = await fetch(`${API_BASE}/api/scope/context?year=${YEAR}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = (await res.json()) as ScopeData;
        setData(json);
      } catch (e) {
        setErr(e instanceof Error ? e.message : String(e));
        setData(null);
      }
    })();
  }, []);

  const title = useMemo(() => data?.meta?.title ?? "Scope & Context", [data]);

  async function callAgent(command: AgentCommand, answer?: string): Promise<AgentResponse> {
    const url = `${API_BASE}/api/scope/agent`;

    const payload = {
      year: YEAR,
      command,
      draft: data ?? null,
      answer: answer ?? null,
    };

    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      throw new Error(`HTTP ${res.status} @ ${url}${txt ? ` | ${txt}` : ""}`);
    }

    return (await res.json()) as AgentResponse;
  }

  function normalizeCommand(text: string): AgentCommand | null {
    const t = text.trim().toLowerCase();
    const map: Record<string, AgentCommand> = {
      "/help": "help",
      "/commands": "commands",
      "/fill": "fill",
      "/autofill": "autofill",
      "/load": "load",
      "/submit": "submit",
      "/reset": "reset",
      "/cancel": "cancel",
      "/yes": "yes",
      "/no": "no",
      "/exit": "exit",
    };
    return map[t] ?? null;
  }

  async function handleLoadSelection(opt: LoadOption) {
    if (sending) return;
    setSending(true);

    try {
      // show what user clicked
      setMessages((prev) => [...prev, { role: "user", content: opt.label }]);

      const resp = await callAgent("load", opt.id);

      if (resp.draft) setData(resp.draft);

      setMessages((prev) => [...prev, { role: "assistant", content: resp.message }]);
      setLoadOptions(resp.load_options ?? null);
      setFillQuestion(resp.next_question ?? null);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `⚠️ ${e instanceof Error ? e.message : String(e)}` },
      ]);
    } finally {
      setSending(false);
    }
  }

  async function onSend() {
    const raw = input;
    const text = raw.trim();
    if (!text || sending) return;

    // echo user message
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setSending(true);

    try {
      // Helper: parse "/cmd arg..." (we keep exact commands for other paths)
      const lower = text.toLowerCase();
      const loadArg = lower.startsWith("/load ") ? text.slice(6).trim() : null;

      // If we're in conversation (/fill) mode:
      // - allow /undo and /exit as commands
      // - otherwise treat the text as the next answer
      if (fillQuestion) {
        const maybeCmd = normalizeCommand(text);

        if (maybeCmd === "exit") {
          const resp = await callAgent(maybeCmd);
          if (resp.draft) setData(resp.draft);

          setMessages((prev) => [...prev, { role: "assistant", content: resp.message }]);

          // exit leaves fill mode
          if (maybeCmd === "exit") setFillQuestion(null);
          return;
        }

        const resp = await callAgent("fill", text);
        if (resp.draft) setData(resp.draft);

        setMessages((prev) => [...prev, { role: "assistant", content: resp.message }]);

        setLoadOptions(resp.load_options ?? null);

        const nq = resp.next_question ?? null;
        setFillQuestion(nq);
        if (nq) setMessages((prev) => [...prev, { role: "assistant", content: nq }]);
        return;
      }

      // Command mode
      let cmd = normalizeCommand(text);

      // Support "/load v2" (or "/load 2026-Scope-XYZ-v2.json")
      let answer: string | undefined = undefined;
      if (!cmd && loadArg !== null) {
        cmd = "load";
        answer = loadArg;
      }

      if (!cmd) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content:
              "I’m in command mode.\n\n" +
              "Type /commands to see the full list.\n" +
              "Tip: use /fill to start conversation mode.",
          },
        ]);
        return;
      }

      const resp = await callAgent(cmd, answer);
      if (resp.draft) setData(resp.draft);

      setMessages((prev) => [...prev, { role: "assistant", content: resp.message }]);

      setLoadOptions(resp.load_options ?? null);

      const nq = resp.next_question ?? null;
      setFillQuestion(nq);
      if (nq) setMessages((prev) => [...prev, { role: "assistant", content: nq }]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `⚠️ ${e instanceof Error ? e.message : String(e)}` },
      ]);
    } finally {
      setSending(false);
    }
  }

  if (err) {
    return (
      <div className="rounded-2xl bg-rose-500/15 p-5 ring-1 ring-rose-500/25 border border-rose-500/20">
        <div className="text-sm text-rose-200">Error loading Scope & Context: {err}</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="rounded-2xl bg-white/5 p-6 ring-1 ring-white/10 border border-white/10">
        <div className="text-sm text-slate-300">Loading Scope & Context…</div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      {/* LEFT (2/3) - DOCUMENT VIEW (SCROLLABLE) */}
      <section className="lg:col-span-2 rounded-2xl bg-white/5 ring-1 ring-white/10 border border-white/10 overflow-hidden">
        {/* Header area stays fixed inside the card */}
        <div className="p-6 border-b border-white/10">
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-slate-100">
            {renderWithPlaceholders(title)}
          </h1>
          <div className="mt-2 text-sm text-slate-400">
            Year: <span className="text-slate-200">{data.meta.year}</span> • Version:{" "}
            <span className="text-slate-200">{data.meta.version}</span>
          </div>
        </div>

        {/* Scrollable content area */}
        <div className="p-6 overflow-y-auto max-h-[70vh]">
          <div className="space-y-8">
            {data.sections.map((section) => (
              <article key={section.id} className="space-y-3">
                <h2 className="text-lg md:text-xl font-semibold text-slate-100">
                  {renderWithPlaceholders(section.title)}
                </h2>

                <p className="text-sm md:text-base leading-relaxed text-slate-300">
                  {renderWithPlaceholders(section.body)}
                </p>

                {section.bullets && section.bullets.length > 0 && (
                  <ul className="list-disc pl-6 text-sm md:text-base text-slate-300 space-y-1">
                    {section.bullets.map((bullet, idx) => (
                      <li key={idx}>{renderWithPlaceholders(bullet)}</li>
                    ))}
                  </ul>
                )}
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* RIGHT (1/3) - AGENT CHAT */}
      <aside className="h-[calc(100vh-140px)] overflow-y-auto rounded-2xl bg-white/5 p-6 ring-1 ring-white/10 border border-white/10">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-slate-100">Assistant</h3>
          <span className="text-xs text-slate-400">
            {sending ? "Working…" : fillQuestion ? "Conversation mode" : "Command mode"}
          </span>
        </div>

        <div className="mt-4 flex-1 min-h-[360px] rounded-xl bg-black/20 ring-1 ring-white/10 border border-white/10 p-4 overflow-y-auto space-y-3">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`rounded-xl px-3 py-2 text-sm whitespace-pre-wrap ${
                m.role === "user"
                  ? "ml-6 bg-sky-500/15 text-sky-100 ring-1 ring-sky-500/25"
                  : "mr-6 bg-white/5 text-slate-200 ring-1 ring-white/10"
              }`}
            >
              <div className="text-[11px] opacity-70 mb-1">{m.role === "user" ? "You" : "Assistant"}</div>
              {m.content}
            </div>
          ))}

          {sending ? (
            <div className="mr-6 rounded-xl bg-white/5 text-slate-200 ring-1 ring-white/10 px-3 py-2 text-sm">
              <div className="text-[11px] opacity-70 mb-1">Assistant</div>
              Thinking…
            </div>
          ) : null}

          {/* /load choices */}
          {loadOptions && loadOptions.length > 0 ? (
            <div className="mt-2 space-y-2">
              {loadOptions.map((opt) => (
                <button
                  key={opt.id}
                  onClick={() => handleLoadSelection(opt)}
                  disabled={sending}
                  className="w-full rounded-xl bg-indigo-600/15 px-4 py-3 text-left text-sm text-slate-100 ring-1 ring-indigo-500/20 border border-indigo-500/20 hover:bg-indigo-600/25 disabled:opacity-50"
                >
                  {opt.label}
                </button>
              ))}
            </div>
          ) : null}

          <div ref={chatBottomRef} />
        </div>

        <div className="mt-4 flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") onSend();
            }}
            placeholder={fillQuestion ? "Answer the question…" : "Type a command (e.g., /help)…"}
            className="flex-1 rounded-xl bg-white/5 px-4 py-3 text-sm text-slate-100 placeholder:text-slate-500 ring-1 ring-white/10 border border-white/10 focus:outline-none focus:ring-2 focus:ring-sky-500/40"
            disabled={sending}
          />

          <button
            onClick={onSend}
            disabled={sending || !input.trim()}
            className="rounded-xl bg-indigo-600/90 px-4 py-3 text-sm font-semibold text-white hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>

        <div className="mt-2 text-xs text-slate-500">
          <div>
            Command mode: <span className="text-slate-300">/help /commands /fill /autofill /load /submit /reset /cancel</span>
          </div>
          <div>
            Conversation mode: <span className="text-slate-300">/exit</span>
          </div>
          {fillQuestion ? <div className="mt-1">Conversation mode is active — your next message is treated as an answer.</div> : null}
        </div>
      </aside>
    </div>
  );
}
