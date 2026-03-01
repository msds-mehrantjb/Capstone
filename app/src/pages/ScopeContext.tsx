import React, { useEffect, useMemo, useRef, useState } from "react";
import { ShieldCheck } from "lucide-react";

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
    source_file?: string;
  };
  sections: Section[];
}

type ChatMessage = { role: "user" | "assistant"; content: string };

type AgentCommand =
  | "help"
  | "commands"
  | "fill"
  | "exit"
  | "autofill"
  | "load"
  | "submit"
  | "reset"
  | "cancel"
  | "yes"
  | "no";

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
  const parts = (text ?? "").split(/(\[[^\]]+\])/g);

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

function stripSlash(cmd: string) {
  const t = cmd.trim();
  return t.startsWith("/") ? t.slice(1) : t;
}

export default function ScopeContext() {
  const [data, setData] = useState<ScopeData | null>(null);
  const [err, setErr] = useState<string | null>(null);

  // sidebar
  const [selectedStep, setSelectedStep] = useState<number>(1);

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

  // If non-null -> conversation/fill mode is active.
  const [fillQuestion, setFillQuestion] = useState<string | null>(null);

  // Buttons coming from backend (used for /load sample options AND /fill menus)
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

  async function callAgent(commandRaw: string, answer?: string): Promise<AgentResponse> {
    const command = stripSlash(commandRaw).toLowerCase() as AgentCommand;
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
    const t = stripSlash(text).trim().toLowerCase();

    const map: Record<string, AgentCommand> = {
      help: "help",
      commands: "commands",
      fill: "fill",
      autofill: "autofill",
      load: "load",
      submit: "submit",
      reset: "reset",
      cancel: "cancel",
      yes: "yes",
      no: "no",
      exit: "exit",
    };

    return map[t] ?? null;
  }

  async function handleLoadSelection(opt: LoadOption) {
      if (sending) return;
      setSending(true);

      try {
        setMessages((prev) => [...prev, { role: "user", content: opt.label }]);

        let resp: AgentResponse;

        if (fillQuestion === "__FILL__") {
          // Fill menu (s1..s6)
          resp = await callAgent("fill", opt.id);
        } else if (fillQuestion === "__LOAD__") {
          // Autofill menu (financial/healthcare/sample/base)
          resp = await callAgent("autofill", opt.id);
        } else {
          // Generic fallback (if you ever reuse load_options for /load)
          resp = await callAgent("load", opt.id);
        }

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

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setSending(true);

    try {
      const lower = text.toLowerCase();
      const loadArg = lower.startsWith("/load ") ? text.slice(6).trim() : null;

      // Conversation (fill) mode
      if (fillQuestion) {
        const maybeCmd = normalizeCommand(text);

        if (maybeCmd) {
          const resp = await callAgent(maybeCmd);
          if (resp.draft) setData(resp.draft);

          setMessages((prev) => [...prev, { role: "assistant", content: resp.message }]);
          setLoadOptions(resp.load_options ?? null);
          setFillQuestion(resp.next_question ?? null);
          return;
        }

        const resp = await callAgent("fill", text);
        if (resp.draft) setData(resp.draft);

        setMessages((prev) => [...prev, { role: "assistant", content: resp.message }]);
        setLoadOptions(resp.load_options ?? null);
        setFillQuestion(resp.next_question ?? null);
        return;
      }

      // Command mode
      let cmd = normalizeCommand(text);

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

  const NAV_ITEMS = [
    { step: 1, name: "Scope & Context", href: "#/scope" },
    { step: 2, name: "Asset Inventory & CIA", href: "#/" },
    { step: 3, name: "Threats & Vulnerabilities", href: "#/" },
    { step: 4, name: "Existing Controls & Posture", href: "#/" },
    { step: 5, name: "Risk Analysis", href: "#/" },
    { step: 6, name: "Risk Evaluation", href: "#/" },
    { step: 7, name: "Risk Treatment", href: "#/" },
    { step: 8, name: "Annex A & SoA", href: "#/" },
    { step: 9, name: "Action Plan / Implementation", href: "#/" },
    { step: 10, name: "Monitoring & Improvement", href: "#/" },
    { step: 11, name: "Final Deliverables", href: "#/" },
  ];

  return (
    <div className="min-h-screen bg-[#070A12] text-slate-50">
      <div className="flex min-h-screen">
        {/* Sidebar */}
        <aside className="w-[280px] border-r border-white/10 bg-[#060815]">
          <div className="px-6 py-6">
            <div className="flex items-center gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-xl bg-sky-500/15 ring-1 ring-sky-500/25">
                <ShieldCheck className="h-5 w-5 text-sky-200" />
              </div>
              <div>
                <div className="text-lg font-semibold tracking-tight">ISO 27001</div>
                <div className="text-sm text-slate-400">Audit Lifecycle</div>
              </div>
            </div>
          </div>

          <nav className="px-3">
            {NAV_ITEMS.map((item) => {
              const active = selectedStep === item.step;
              return (
                <button
                  key={item.step}
                  onClick={() => {
                    setSelectedStep(item.step);
                    window.location.hash = item.href;
                  }}
                  className={`group mb-1 flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left text-sm ${
                    active ? "bg-white/5 ring-1 ring-white/10" : "hover:bg-white/5"
                  }`}
                >
                  <span
                    className={`grid h-7 w-7 place-items-center rounded-lg text-xs ${
                      active
                        ? "bg-sky-500/15 text-sky-200 ring-1 ring-sky-500/25"
                        : "bg-white/5 text-slate-300 ring-1 ring-white/10"
                    }`}
                  >
                    {item.step}
                  </span>
                  <span className={`${active ? "text-slate-50" : "text-slate-200"}`}>{item.name}</span>
                </button>
              );
            })}
          </nav>

          <button
            onClick={() => (window.location.hash = "#/")}
            className="mx-4 mt-6 mb-4 w-[calc(100%-2rem)] rounded-xl bg-indigo-600/90 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-600 transition"
          >
            Dashboard
          </button>
        </aside>

        {/* Main */}
        <main className="flex-1">
           
            <header className="sticky top-0 z-20 border-b border-white/10 bg-[#070A12]/70 backdrop-blur">
              <div className="mx-auto flex max-w-6xl items-center justify-center px-6 py-6">
                <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-slate-100 text-center">
                  ISO 27001 Scope & Context
                </h1>
              </div>
            </header>

          <div className="mx-auto max-w-6xl px-6 py-8">
            {err ? (
              <div className="rounded-2xl bg-rose-500/15 p-5 ring-1 ring-rose-500/25 border border-rose-500/20">
                <div className="text-sm text-rose-200">Error loading Scope & Context: {err}</div>
              </div>
            ) : !data ? (
              <div className="rounded-2xl bg-white/5 p-6 ring-1 ring-white/10 border border-white/10">
                <div className="text-sm text-slate-300">Loading Scope & Context…</div>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                {/* LEFT (2/3) - DOCUMENT VIEW */}
                <section className="lg:col-span-2 rounded-2xl bg-white/5 ring-1 ring-white/10 border border-white/10 overflow-hidden">
                  <div className="p-6 border-b border-white/10">
                    <h2 className="text-xl md:text-2xl font-bold tracking-tight text-slate-100">
                      {renderWithPlaceholders(title)}
                    </h2>
                    <div className="mt-2 text-sm text-slate-400">
                      Year: <span className="text-slate-200">{data.meta.year}</span> • Version:{" "}
                      <span className="text-slate-200">{data.meta.version}</span>
                    </div>
                  </div>

                  <div className="p-6 overflow-y-auto max-h-[70vh]">
                    <div className="space-y-8">
                      {data.sections.map((section) => (
                        <article key={section.id} className="space-y-3">
                          <h3 className="text-lg md:text-xl font-semibold text-slate-100">
                            {renderWithPlaceholders(section.title)}
                          </h3>

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
                <aside className="rounded-2xl bg-white/5 p-6 ring-1 ring-white/10 border border-white/10 flex flex-col h-[75vh]">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-slate-100">Assistant</h3>
                    <span className="text-xs text-slate-400">
                      {sending 
                          ? "Working…"
                          : fillQuestion === "__FILL__"
                            ? "Conversation mode"
                            : fillQuestion === "__LOAD__"
                              ? "Load menu"
                              : "Command mode"}
                    </span>
                  </div>

                  <div className="mt-4 flex-1 rounded-xl bg-black/20 ring-1 ring-white/10 border border-white/10 p-4 overflow-y-auto space-y-3">
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
                      placeholder={fillQuestion ? "Choose a section / answer…" : "Type a command (e.g., /help)…"}
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
                      Command mode:{" "}
                      <span className="text-slate-300">/help /commands /fill /autofill /load /submit /reset /cancel</span>
                    </div>
                    <div>
                      Conversation mode: <span className="text-slate-300">/exit</span>
                    </div>
                  </div>
                </aside>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
