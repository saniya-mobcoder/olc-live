"use client";

import { Button, Input, Tabs } from "@/components/ui";

type Msg = { role: "user" | "assistant"; text: string; sources?: string[] };

export function CopilotPanel({
  mode,
  onModeChange,
  chat,
  chatInput,
  onChatInput,
  onSend,
  matchId,
  compact = false,
}: {
  mode: "match" | "support";
  onModeChange: (m: "match" | "support") => void;
  chat: Msg[];
  chatInput: string;
  onChatInput: (v: string) => void;
  onSend: (override?: string) => void;
  matchId?: string | null;
  compact?: boolean;
}) {
  const prompts =
    mode === "match"
      ? [
          "Summarize the shortlist",
          "Why was the top pick recommended?",
          "Compare rank 1 and rank 2",
        ]
      : [
          "How do I run a match?",
          "What do hard gates mean?",
          "How does hybrid ranking work?",
        ];

  return (
    <div
      className={`flex flex-col ${compact ? "card-surface h-full min-h-[22rem] p-4" : "space-y-4"}`}
    >
      {!compact ? (
        <div>
          <h2 className="font-display text-3xl text-ink">Producer copilot</h2>
          <p className="mt-1 text-sm text-ink-muted">
            Grounded answers from match context or product FAQ.
          </p>
        </div>
      ) : (
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-eyebrow text-ink-muted">
            Assist
          </p>
          <h3 className="font-display text-lg text-ink">Copilot</h3>
        </div>
      )}

      <Tabs
        items={[
          { id: "match", label: "Match" },
          { id: "support", label: "Support" },
        ]}
        value={mode}
        onChange={onModeChange}
      />

      <p className="text-xs text-ink-muted">
        {mode === "match"
          ? matchId
            ? `Grounded on ${matchId}`
            : "Run a match to ground answers"
          : "FAQ support mode"}
      </p>

      <div className="flex flex-wrap gap-2">
        {prompts.map((p) => (
          <Button
            key={p}
            type="button"
            size="sm"
            variant="subtle"
            onClick={() => onSend(p)}
          >
            {p}
          </Button>
        ))}
      </div>

      <div
        className={`space-y-3 overflow-y-auto ${compact ? "max-h-64 flex-1" : "card-surface max-h-[28rem] p-4"}`}
      >
        {chat.map((m, i) => (
          <div
            key={`${m.role}-${i}`}
            className={`rounded-xl px-3 py-2 text-sm ${
              m.role === "user"
                ? "ml-6 border border-cyan/25 bg-info-bg text-ink"
                : "mr-4 border border-line bg-white/[0.04] text-ink-soft"
            }`}
          >
            <p className="whitespace-pre-wrap">{m.text}</p>
            {m.sources?.length ? (
              <div className="mt-2 flex flex-wrap gap-1">
                {m.sources.map((s) => (
                  <span
                    key={s}
                    className="rounded border border-line px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-ink-muted"
                  >
                    {s}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        ))}
      </div>

      <div className="flex gap-2">
        <Input
          value={chatInput}
          onChange={(e) => onChatInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSend();
            }
          }}
          placeholder="Ask about the cast…"
        />
        <Button type="button" onClick={() => onSend()}>
          Send
        </Button>
      </div>
    </div>
  );
}
