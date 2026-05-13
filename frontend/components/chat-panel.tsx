"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import type { AnalyzeResponse, ChatMessage } from "@/types";
import { sendChatMessage } from "@/lib/api";

interface Props {
  analysisData: AnalyzeResponse;
}

const SUGGESTED_PROMPTS = [
  "Why were my trades flagged?",
  "What's my biggest weakness?",
  "How can I reduce revenge trading?",
  "Explain my calm score",
  "What patterns do you see?",
];

export default function ChatPanel({ analysisData }: Props) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (open && inputRef.current) {
      inputRef.current.focus();
    }
  }, [open]);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || loading) return;

      const userMsg: ChatMessage = { role: "user", text: text.trim() };
      const updatedMessages = [...messages, userMsg];
      setMessages(updatedMessages);
      setInput("");
      setLoading(true);

      try {
        const res = await sendChatMessage(
          updatedMessages.map((m) => ({ role: m.role, text: m.text })),
          analysisData as any
        );

        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: "Chat failed" }));
          throw new Error(err.detail || "Chat failed");
        }

        const data = await res.json();
        setMessages((prev) => [
          ...prev,
          { role: "model", text: data.reply },
        ]);
      } catch (err: any) {
        setMessages((prev) => [
          ...prev,
          {
            role: "model",
            text: `⚠️ ${err.message || "Something went wrong. Please try again."}`,
          },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [messages, loading, analysisData]
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  return (
    <>
      {/* Floating chat button */}
      <button
        onClick={() => setOpen(!open)}
        className={`fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full shadow-lg flex items-center justify-center transition-all duration-300 hover:scale-105 active:scale-95 ${
          open
            ? "bg-muted text-foreground ring-1 ring-border"
            : "bg-gradient-to-br from-blue-600 to-violet-600 text-white"
        }`}
        aria-label={open ? "Close chat" : "Open AI chat"}
      >
        {open ? (
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 6 6 18" /><path d="m6 6 12 12" />
          </svg>
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        )}
      </button>

      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-24 right-6 z-50 w-[380px] max-w-[calc(100vw-2rem)] h-[520px] max-h-[calc(100vh-8rem)] rounded-2xl border border-border/50 bg-background shadow-2xl flex flex-col animate-scale-in overflow-hidden">
          {/* Header */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-border/50 bg-muted/30">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-violet-600 flex items-center justify-center flex-shrink-0">
              <span className="text-white text-xs font-bold">AI</span>
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold truncate">BiasLens Chat</p>
              <p className="text-[10px] text-muted-foreground">Ask about your flagged trades & biases</p>
            </div>
            <button
              onClick={() => setMessages([])}
              className="ml-auto text-muted-foreground hover:text-foreground transition-colors p-1"
              title="Clear chat"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 6h18" /><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" /><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
              </svg>
            </button>
          </div>

          {/* Messages area */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
            {messages.length === 0 && !loading && (
              <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
                <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-600/10 to-violet-600/10 flex items-center justify-center">
                  <span className="text-2xl">💬</span>
                </div>
                <div>
                  <p className="text-sm font-medium">Ask me anything</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    I can explain flagged trades, bias scores, and give advice
                  </p>
                </div>
                <div className="flex flex-wrap gap-1.5 justify-center max-w-[280px]">
                  {SUGGESTED_PROMPTS.map((prompt) => (
                    <button
                      key={prompt}
                      onClick={() => sendMessage(prompt)}
                      className="text-[11px] px-2.5 py-1.5 rounded-lg bg-muted/50 hover:bg-muted border border-border/50 text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-gradient-to-br from-blue-600 to-violet-600 text-white rounded-br-md"
                      : "bg-muted/50 border border-border/50 text-foreground rounded-bl-md"
                  }`}
                >
                  <div className="whitespace-pre-wrap break-words">{msg.text}</div>
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="bg-muted/50 border border-border/50 rounded-2xl rounded-bl-md px-4 py-3">
                  <div className="flex gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-muted-foreground/40 animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-2 h-2 rounded-full bg-muted-foreground/40 animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-2 h-2 rounded-full bg-muted-foreground/40 animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <form
            onSubmit={handleSubmit}
            className="flex items-center gap-2 px-3 py-3 border-t border-border/50 bg-muted/20"
          >
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about your trades..."
              disabled={loading}
              className="flex-1 bg-background border border-border/50 rounded-xl px-3.5 py-2.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/50 disabled:opacity-50 transition-all"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-600 to-violet-600 text-white flex items-center justify-center flex-shrink-0 disabled:opacity-40 hover:opacity-90 transition-opacity active:scale-95"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="m22 2-7 20-4-9-9-4Z" /><path d="M22 2 11 13" />
              </svg>
            </button>
          </form>
        </div>
      )}
    </>
  );
}
