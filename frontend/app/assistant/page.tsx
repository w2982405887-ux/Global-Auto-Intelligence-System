"use client";

import {
  ArrowLeft, Bot, Calculator, CheckCircle2, ChevronRight, Circle, Clock3,
  Database, ExternalLink, FileText, Info, LoaderCircle, Menu, Paperclip,
  MessageSquarePlus, PanelRightClose, PanelRightOpen, Search, Send, ShieldCheck, Sparkles, Trash2, X,
} from "lucide-react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useEffect, useRef, useState } from "react";
import { API_BASE_URL, ApiError, getCsrfHeaders } from "../lib/api";

// ── Types ──

type MsgRole = "user" | "assistant" | "tool" | "ask";

interface ChatMsg {
  id: string;
  role: MsgRole;
  content: string;
  toolCalls?: { name: string; args: string; status: "running" | "done" | "error"; summary?: string }[];
  askOptions?: { label: string; value: Record<string, unknown> }[];
  timestamp: string;
}

interface ConversationMeta {
  conversation_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  status: string;
}

interface AssistantAttachment {
  attachment_id: string;
  filename: string;
  mime_type: string;
  size: number;
}

// A tool call can be emitted more than once while the gateway retries or
// resumes a stream.  Keep the original display value, but use a stable
// representation for comparing arguments so calls with different parameters
// are never accidentally collapsed into one UI card.
function stableJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map((item) => stableJson(item)).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value as Record<string, unknown>).sort().map((key) => `${JSON.stringify(key)}:${stableJson((value as Record<string, unknown>)[key])}`).join(",")}}`;
  }
  const encoded = JSON.stringify(value);
  return encoded === undefined ? "undefined" : encoded;
}

function canonicalToolArgs(value: unknown): string {
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) return "";
    try {
      return stableJson(JSON.parse(trimmed));
    } catch {
      return trimmed;
    }
  }
  return stableJson(value ?? "");
}

function displayToolArgs(value: unknown): string {
  if (typeof value === "string") return value;
  if (value === undefined || value === null) return "";
  try { return JSON.stringify(value); } catch { return String(value); }
}

function isAbortedStreamError(error: unknown, signal: AbortSignal): boolean {
  const message = error instanceof Error ? error.message : String(error || "");
  return signal.aborted ||
    (error instanceof DOMException && error.name === "AbortError") ||
    /body(stream)?buffer.*aborted|stream.*aborted|aborted/i.test(message);
}

function isLlmConfigurationError(error: unknown): boolean {
  const message = error instanceof Error ? error.message : String(error || "");
  return /(?:llm|openclaw|gateway).*(?:api[\s_-]*key|credential|authentication|unauthori[sz]ed)|(?:api[\s_-]*key|llm_api_key).*(?:missing|invalid|not configured|未配置|无效|缺失)|配置了?\s*llm\s*api\s*key/i.test(message);
}

function AssistantMarkdown({ content }: { content: string }) {
  return (
    <div className="asst-markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Keep generated links inside a safe, explicit browser target.
          a: ({ node, ...props }) => {
            void node;
            return <a {...props} target="_blank" rel="noreferrer" />;
          },
          table: ({ node, ...props }) => {
            void node;
            return <div className="asst-table-wrap"><table {...props} /></div>;
          },
          pre: ({ node, ...props }) => {
            void node;
            return <pre className="asst-code-block" {...props} />;
          },
          code: ({ node, className, children, ...props }) => {
            void node;
            return <code className={className || "asst-inline-code"} {...props}>{children}</code>;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

// ── Page ──

export default function AssistantPage() {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationMeta[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attachments, setAttachments] = useState<AssistantAttachment[]>([]);
  const [uploading, setUploading] = useState(false);
  const [wsOpen, setWsOpen] = useState(true);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    void refreshConversations();
  }, []);

  async function refreshConversations() {
    const resp = await fetch(`${API_BASE_URL}/assistant/conversations`, {
      headers: { Accept: "application/json" },
      credentials: "include",
    });
    if (!resp.ok) return;
    const data = (await resp.json()) as ConversationMeta[];
    setConversations(data.filter((item) => item.status !== "ARCHIVED"));
  }

  async function loadConversation(id: string) {
    if (busy) return;
    setError(null);
    setAttachments([]);
    setConversationId(id);
    const resp = await fetch(`${API_BASE_URL}/assistant/conversations/${id}/messages`, {
      headers: { Accept: "application/json" },
      credentials: "include",
    });
    if (!resp.ok) {
      setMessages([]);
      setError(`无法读取历史会话：${resp.status}`);
      return;
    }
    const data = await resp.json();
    setMessages((data?.messages ?? []) as ChatMsg[]);
  }

  async function archiveConversation(id: string) {
    if (busy) return;
    await fetch(`${API_BASE_URL}/assistant/conversations/${id}`, {
      method: "DELETE",
      headers: getCsrfHeaders(),
      credentials: "include",
    });
    if (conversationId === id) {
      setConversationId(null);
      setMessages([]);
      setAttachments([]);
    }
    await refreshConversations();
  }

  function startNewConversation() {
    if (busy) return;
    setConversationId(null);
    setMessages([]);
    setInput("");
    setAttachments([]);
    setError(null);
  }

  async function uploadFiles(fileList: FileList | null) {
    if (!fileList || fileList.length === 0 || busy || uploading) return;
    setUploading(true);
    setError(null);
    try {
      let nextConversationId = conversationId;
      const uploaded: AssistantAttachment[] = [];
      for (const file of Array.from(fileList)) {
        const form = new FormData();
        form.append("file", file);
        if (nextConversationId) form.append("conversation_id", nextConversationId);
        const response = await fetch(`${API_BASE_URL}/assistant/files`, { method: "POST", body: form, headers: getCsrfHeaders(), credentials: "include" });
        const data = await response.json().catch(() => null);
        if (!response.ok) throw new Error(data?.detail || `附件上传失败：${response.status}`);
        nextConversationId = data.conversation_id || nextConversationId;
        uploaded.push(data as AssistantAttachment);
      }
      if (nextConversationId) setConversationId(nextConversationId);
      setAttachments((prev) => [...prev, ...uploaded]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "附件上传失败");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function send() {
    const text = input.trim();
    if ((!text && attachments.length === 0) || busy || uploading) return;
    const pendingAttachments = [...attachments];
    setInput("");
    setAttachments([]);
    setError(null);

    const attachmentLabel = pendingAttachments.length
      ? `\n\n附件：${pendingAttachments.map((item) => item.filename).join("、")}`
      : "";
    const userMsg: ChatMsg = { id: Date.now().toString(), role: "user", content: (text || "请分析附件") + attachmentLabel, timestamp: new Date().toISOString() };
    const aiMsg: ChatMsg = { id: (Date.now() + 1).toString(), role: "assistant", content: "思考中…", timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg, aiMsg]);
    setBusy(true);
    let partialStreamContent = "";
    const ctrl = new AbortController();
    // Do not put a fixed ceiling on the complete agent run.  A normal run can
    // include several tools and a web search.  Only the initial connection and
    // a genuinely idle stream are timed out; every received chunk re-arms the
    // idle timer below.
    const CONNECT_TIMEOUT_MS = 30_000;
    const STREAM_IDLE_TIMEOUT_MS = 300_000;
    let connectTimeoutId: ReturnType<typeof setTimeout> | null = null;
    let idleTimeoutId: ReturnType<typeof setTimeout> | null = null;
    let abortReason: "connect_timeout" | "idle_timeout" | null = null;
    const clearConnectTimeout = () => {
      if (connectTimeoutId !== null) {
        clearTimeout(connectTimeoutId);
        connectTimeoutId = null;
      }
    };
    const clearIdleTimeout = () => {
      if (idleTimeoutId !== null) {
        clearTimeout(idleTimeoutId);
        idleTimeoutId = null;
      }
    };
    const armIdleTimeout = () => {
      clearIdleTimeout();
      idleTimeoutId = setTimeout(() => {
        abortReason = "idle_timeout";
        ctrl.abort();
      }, STREAM_IDLE_TIMEOUT_MS);
    };
    const handleConnectTimeout = () => {
      abortReason = "connect_timeout";
      ctrl.abort();
    };
    // Record the reason before AbortError reaches the fetch/reader catch block.
    connectTimeoutId = setTimeout(handleConnectTimeout, CONNECT_TIMEOUT_MS);

    try {
      // The backend owns the OpenClaw token and tool loop. The browser sends
      // only the conversation id, text, and opaque attachment ids.
      const question = text;
      const resp = await fetch(`${API_BASE_URL}/assistant/chat`, {
        method: "POST",
        headers: { Accept: "text/event-stream, application/json", "Content-Type": "application/json", ...getCsrfHeaders() },
        credentials: "include",
        body: JSON.stringify({
          conversation_id: conversationId,
          message: question,
          attachment_ids: pendingAttachments.map((item) => item.attachment_id),
          stream: true,
        }),
        signal: ctrl.signal,
      });
      clearConnectTimeout();

      if (!resp.ok) {
        const errText = await resp.text().catch(() => resp.statusText);
        throw new Error(`${resp.status}: ${errText.slice(0, 200)}`);
      }

      const contentType = resp.headers.get("content-type") || "";
      if (!contentType.toLowerCase().includes("text/event-stream")) {
        // Backward-compatible path for an older backend or a deployment
        // proxy that still returns the original JSON contract.
        const data = await resp.json().catch(() => null) as Record<string, unknown> | null;
        if (typeof data?.conversation_id === "string") setConversationId(data.conversation_id);
        const finalContent =
          data?.narrative || data?.content || data?.message ||
          (data?.answer as Record<string, unknown> | undefined)?.narrative ||
          (data?.answer as Record<string, unknown> | undefined)?.content ||
          data?.headline || "Agent 返回空响应";
        setMessages((prev) => {
          const updated = [...prev];
          const idx = updated.findIndex((m) => m.id === aiMsg.id);
          if (idx >= 0) {
            updated[idx] = {
              ...updated[idx],
              content: String(finalContent || "Agent 返回空响应"),
              toolCalls: Array.isArray(data?.tool_calls) ? data.tool_calls as ChatMsg["toolCalls"] : undefined,
            };
          }
          return updated;
        });
      } else {
        const reader = resp.body?.getReader();
        if (!reader) throw new Error("后端未返回可读取的流");
        armIdleTimeout();
        const decoder = new TextDecoder();
        let buffer = "";
        let streamedContent = "";
        const toolCalls: NonNullable<ChatMsg["toolCalls"]> = [];
        let completed = false;

        const updateAssistant = (patch: Partial<ChatMsg>) => {
          setMessages((prev) => {
            const updated = [...prev];
            const idx = updated.findIndex((m) => m.id === aiMsg.id);
            if (idx >= 0) updated[idx] = { ...updated[idx], ...patch };
            return updated;
          });
        };

        const handleEvent = (block: string) => {
          const lines = block.split(/\r?\n/);
          let eventName = "message";
          const dataLines: string[] = [];
          for (const line of lines) {
            if (line.startsWith("event:")) eventName = line.slice(6).trim();
            else if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
          }
          if (dataLines.length === 0) return;
          let data: Record<string, unknown>;
          try { data = JSON.parse(dataLines.join("\n")) as Record<string, unknown>; }
          catch { return; }

          const conversation = data.conversation_id;
          if (typeof conversation === "string" && conversation) setConversationId(conversation);
          if (eventName === "answer_delta") {
            const textDelta = String(data.text || "");
            if (textDelta) {
              streamedContent += textDelta;
              partialStreamContent = streamedContent;
              updateAssistant({ content: streamedContent });
            }
          } else if (eventName === "tool_started") {
            const name = String(data.tool_name || data.name || "unknown");
            const rawArgs = data.args;
            const args = displayToolArgs(rawArgs);
            const signature = canonicalToolArgs(rawArgs);
            // Merge only an exact duplicate (same tool and same arguments).
            // The same tool with different arguments represents a real second
            // call and must remain visible to the user.
            const existing = toolCalls.find((item) => item.name === name && canonicalToolArgs(item.args) === signature && item.status === "running");
            if (!existing) toolCalls.push({ name, args, status: "running" });
            updateAssistant({ toolCalls: [...toolCalls] });
          } else if (eventName === "tool_completed" || eventName === "tool_failed") {
            const name = String(data.tool_name || data.name || "unknown");
            const status = eventName === "tool_completed" ? "done" : "error";
            const completionArgs = data.args;
            const completionSignature = canonicalToolArgs(completionArgs);
            const existing = [...toolCalls].reverse().find((item) => {
              if (item.name !== name || item.status !== "running") return false;
              // Most gateway completion events omit args.  In that case use the
              // latest running invocation; otherwise require an exact match.
              return completionArgs === undefined || canonicalToolArgs(item.args) === completionSignature;
            });
            if (existing) existing.status = status;
            else if (!toolCalls.some((item) => item.name === name && canonicalToolArgs(item.args) === completionSignature && item.status === status)) {
              toolCalls.push({ name, args: displayToolArgs(completionArgs), status, summary: String(data.summary || data.error || "") });
            }
            if (existing) existing.summary = String(data.summary || data.error || "");
            updateAssistant({ toolCalls: [...toolCalls] });
          } else if (eventName === "answer_completed") {
            completed = true;
            const narrative = String(data.narrative || streamedContent || "Agent 返回空响应");
            streamedContent = narrative;
            partialStreamContent = narrative;
            updateAssistant({ content: narrative, toolCalls: Array.isArray(data.tool_calls) ? data.tool_calls as ChatMsg["toolCalls"] : [...toolCalls] });
          } else if (eventName === "error") {
            throw new Error(String(data.message || "助手流式处理失败"));
          }
        };

        const consumeBlock = (block: string) => {
          if (block.trim()) handleEvent(block);
        };
        while (true) {
          // Keep the timeout rolling.  A long tool call is healthy as long as
          // the backend continues to send status/heartbeat/data events.
          armIdleTimeout();
          const { value, done } = await reader.read();
          armIdleTimeout();
          buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
          const blocks = buffer.split(/\r?\n\r?\n/);
          buffer = blocks.pop() || "";
          blocks.forEach(consumeBlock);
          if (done) break;
        }
        consumeBlock(buffer);
        if (!completed) {
          if (streamedContent) {
            const interrupted = `${streamedContent}\n\n> ⚠️ 流式连接在完成事件前结束，以上为已接收内容。`;
            partialStreamContent = interrupted;
            updateAssistant({ content: interrupted });
            setError("流式连接提前结束，可重新发送问题继续。");
          } else {
            updateAssistant({ content: "Agent 返回空响应" });
          }
        }
      }
      await refreshConversations();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "连接失败";
      const aborted = isAbortedStreamError(e, ctrl.signal);
      const configurationError = isLlmConfigurationError(e);
      let userMessage = msg;
      let assistantNotice = "";
      if (aborted) {
        const reason = abortReason === "connect_timeout"
          ? "后端连接超时"
          : abortReason === "idle_timeout"
            ? "流式响应长时间没有新数据"
            : "流式连接被中断";
        userMessage = `${reason}，已保留已接收内容，可稍后重试。`;
        assistantNotice = `> ⚠️ ${reason}，以上为已接收内容。`;
      } else if (configurationError) {
        userMessage = `${msg}（请检查后端 OpenClaw/LLM API Key 配置。）`;
        assistantNotice = `> ⚠️ ${msg}\n> 请检查后端 OpenClaw/LLM API Key 配置。`;
      } else {
        // Do not attach an API-key hint to arbitrary network, proxy, or parser
        // errors.  That message was misleading when the stream had already
        // returned successful tool events.
        assistantNotice = `> ⚠️ ${msg || "助手流式处理失败"}`;
      }
      setError(userMessage);
      setMessages((prev) => {
        const updated = [...prev];
        const idx = updated.findIndex((m) => m.id === aiMsg.id);
        if (idx >= 0) {
          const prefix = partialStreamContent ? `${partialStreamContent}\n\n` : "";
          updated[idx] = { ...updated[idx], content: `${prefix}${assistantNotice}` };
        }
        return updated;
      });
    } finally {
      clearConnectTimeout();
      clearIdleTimeout();
      setBusy(false);
    }
  }

  return (
    <main className="asst-page">
      <div className="asst-shell">
        <header className="asst-topbar">
          <Link className="asst-back" href="/"><ArrowLeft size={17} /> 返回</Link>
          <div className="asst-brand">
            <Sparkles size={18} />
            <strong>AI 决策助手</strong>
            <span className="asst-beta">CO-WORK</span>
          </div>
          <button type="button" className="asst-ws-toggle" onClick={() => setWsOpen(!wsOpen)} title={wsOpen ? "收起工作台" : "展开工作台"}>
            {wsOpen ? <PanelRightClose size={17} /> : <PanelRightOpen size={17} />}
          </button>
        </header>

        <div className={`asst-body ${wsOpen ? "ws-open" : ""}`}>
          {/* Chat */}
          <section className="asst-chat">
            <div className="asst-msgs">
              {messages.length === 0 && (
                <div className="asst-empty">
                  <Bot size={44} />
                  <h3>AutoPolicy AI 决策助手</h3>
                  <p>我可以帮你分析马来西亚汽车出口税负、查询政策规则、对比 CBU 与 CKD 方案，并追溯官方依据。</p>
                  <div className="asst-prompts">
                    {[
                      "中国BEV出口马来西亚，CBU和CKD哪个税负更低？",
                      "HEV CBU 的消费税是多少？",
                      "为什么 BEV CBU 进口关税是 30%？",
                    ].map((p) => (
                      <button key={p} type="button" className="asst-prompt-chip" onClick={() => { setInput(p); }}>
                        {p}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((msg) => (
                <div key={msg.id} className={`asst-msg asst-msg-${msg.role}`}>
                  <div className="asst-msg-avatar">
                    {msg.role === "user" ? "👤" : msg.role === "tool" ? "🔧" : "🤖"}
                  </div>
                  <div className="asst-msg-body">
                    <div className="asst-msg-content">
                      {msg.role === "assistant" ? <AssistantMarkdown content={msg.content} /> : msg.content}
                    </div>
                    {msg.toolCalls?.map((tc, i) => (
                      <div key={i} className={`asst-tc-card ${tc.status}`}>
                        <span className="asst-tc-name">{tc.name}</span>
                        {tc.status === "running" ? <LoaderCircle className="spin" size={13} /> : null}
                        {tc.summary && <small className="asst-tc-summary">{tc.summary}</small>}
                      </div>
                    ))}
                    {msg.askOptions && (
                      <div className="asst-ask-opts">
                        {msg.askOptions.map((opt, i) => (
                          <button key={i} type="button" className="asst-ask-btn" onClick={() => setInput(opt.label)}>
                            {opt.label}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {error && (
                <div className="asst-err">
                  {error}
                  <button type="button" className="asst-err-dismiss" onClick={() => setError(null)}><X size={14} /></button>
                </div>
              )}

              <div ref={chatEndRef} />
            </div>

            <div className="asst-input-bar">
              <input
                ref={fileInputRef}
                className="asst-file-input"
                type="file"
                multiple
                accept=".pdf,.docx,.txt,.md,.json,.csv,image/*"
                onChange={(e) => void uploadFiles(e.target.files)}
                disabled={busy || uploading}
              />
              <button
                type="button"
                className="asst-upload-btn"
                onClick={() => fileInputRef.current?.click()}
                disabled={busy || uploading}
                title="上传文件或图片"
              >
                {uploading ? <LoaderCircle className="spin" size={18} /> : <Paperclip size={18} />}
              </button>
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") send(); }}
                placeholder="输入你的问题…"
                disabled={busy}
              />
              <button type="button" onClick={send} disabled={busy || uploading || (!input.trim() && attachments.length === 0)}>
                {busy ? <LoaderCircle className="spin" size={18} /> : <Send size={18} />}
              </button>
            </div>
            {attachments.length > 0 && (
              <div className="asst-attachments">
                {attachments.map((item) => (
                  <span className="asst-attach-chip" key={item.attachment_id}>
                    <FileText size={13} />
                    <span>{item.filename}</span>
                    <button
                      type="button"
                      onClick={() => setAttachments((prev) => prev.filter((entry) => entry.attachment_id !== item.attachment_id))}
                      title="移除附件"
                    >
                      <X size={12} />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </section>

          {/* Workspace */}
          {wsOpen && (
            <aside className="asst-ws">
              <div className="asst-ws-block">
                <div className="asst-history-head">
                  <span className="asst-ws-kicker">历史对话</span>
                  <button type="button" onClick={startNewConversation} title="新建对话" disabled={busy}>
                    <MessageSquarePlus size={15} />
                  </button>
                </div>
                <div className="asst-history-list">
                  {conversations.length === 0 && (
                    <div className="asst-history-empty">暂无历史对话</div>
                  )}
                  {conversations.map((item) => (
                    <div
                      key={item.conversation_id}
                      className={`asst-history-item ${conversationId === item.conversation_id ? "active" : ""}`}
                    >
                      <button type="button" onClick={() => loadConversation(item.conversation_id)} disabled={busy}>
                        <strong>{item.title || item.conversation_id.slice(0, 8)}</strong>
                        <small>
                          <Clock3 size={11} />
                          {item.updated_at ? new Date(item.updated_at).toLocaleString() : "刚刚"}
                        </small>
                      </button>
                      <button
                        type="button"
                        className="asst-history-delete"
                        onClick={() => archiveConversation(item.conversation_id)}
                        title="归档对话"
                        disabled={busy}
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
              <div className="asst-ws-block">
                <span className="asst-ws-kicker">当前状态</span>
                <div className="asst-ws-status">{busy ? "● 分析中" : "○ 待命"}</div>
              </div>
              <div className="asst-ws-block">
                <span className="asst-ws-kicker">提示</span>
                <p className="asst-ws-hint">你可以自由提问。Agent 会自动调用 CBU/CKD 计算器、政策查询和证据追溯。如果需要更多信息，它会主动问你。</p>
              </div>
              <div className="asst-ws-block">
                <span className="asst-ws-kicker">覆盖能力</span>
                <div className="asst-ws-cap-list">
                  <span>✓ CBU 整车进口税计算</span>
                  <span>✓ CKD 散件进口税计算</span>
                  <span>✓ 政策规则查询</span>
                  <span>✓ 官方证据追溯</span>
                  <span>✓ 数据覆盖普查</span>
                  <span>✓ MFN / ACFTA / RCEP 对比</span>
                </div>
              </div>
              <div className="asst-ws-block">
                <span className="asst-ws-kicker">环境</span>
                <code className="asst-ws-env">
                  后端: {API_BASE_URL.startsWith("http") ? API_BASE_URL : "当前页面同源代理 /api/v1"}<br />
                  数据库: PostgreSQL (Docker)<br />
                  市场: MY (马来西亚)
                </code>
              </div>
            </aside>
          )}
        </div>
      </div>
    </main>
  );
}
