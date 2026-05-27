/** @odoo-module **/
import { Component, useState, onMounted, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class AIChatComponent extends Component {
    static template = "dineflow.AIChatComponent";

    setup() {
        this.rpc = useService("rpc");
        this.messageEndRef = useRef("messageEnd");
        this._es = null;
        this._currentJobId = null;
        this._lastStepTime = 0;   // ← timestamp step cuối

        this.state = useState({
            messages: [],
            input: "",
            loading: false,
            currentStep: "",
            lastTokenReport: null,
        });

        onMounted(() => this._loadHistory());
    }

    async _loadHistory() {
        const history = await this.rpc("/dineflow/chat/history", {});
        for (const h of history) {
            this.state.messages.push({ from: "user", text: h.message });
            this.state.messages.push({ from: "bot", text: h.response });
        }
        this._scrollToBottom();
    }

    async sendMessage() {
        const message = this.state.input.trim();
        if (!message || this.state.loading) return;

        this.state.messages.push({ from: "user", text: message });
        this.state.input = "";
        this.state.loading = true;
        this.state.currentStep = "🔄 Đang kết nối...";
        this.state.lastTokenReport = null;
        this._lastStepTime = 0;   // ← reset khi gửi tin mới
        this._scrollToBottom();

        try {
            const result = await this.rpc("/dineflow/chat/async", { message });

            if (result.job_id && result.session_id) {
                this._currentJobId = result.job_id;
                this._openSSE(result.session_id);
            } else {
                this.state.messages.push({ from: "bot", text: result.response || "Không có phản hồi." });
                this.state.loading = false;
                this.state.currentStep = "";
                this._scrollToBottom();
            }
        } catch (e) {
            this.state.messages.push({ from: "bot", text: "Lỗi kết nối AI. Vui lòng thử lại." });
            this.state.loading = false;
            this.state.currentStep = "";
            this._scrollToBottom();
        }
    }

    // ← Hàm mới: set step với delay tối thiểu 600ms
    async _setStep(text) {
        const MIN_DISPLAY_MS = 1000;
        const now = Date.now();
        const elapsed = now - this._lastStepTime;

        if (this._lastStepTime > 0 && elapsed < MIN_DISPLAY_MS) {
            await new Promise(r => setTimeout(r, MIN_DISPLAY_MS - elapsed));
        }

        this.state.currentStep = text;
        this._lastStepTime = Date.now();
        this._scrollToBottom();
    }

    _openSSE(sessionId) {
        if (this._es) {
            this._es.close();
            this._es = null;
        }

        const url = `/dineflow/chat/stream/${sessionId}`;
        this._es = new EventSource(url);

        this._es.onmessage = (e) => {
            try {
                const event = JSON.parse(e.data);

                if (event.type === "status") {
                    this._setStep(event.message);
                }

                if (event.type === "tool_start") {
                    this._setStep(event.message);
                }

                if (event.type === "tool_end") {
                    const tokens = event.tokens ? ` (${event.tokens} tokens)` : "";
                    this._setStep(event.message + tokens);
                }

                if (event.type === "done") {
                    if (event.tokens) {
                        this.state.lastTokenReport = {
                            total:   event.tokens.total || 0,
                            elapsed: event.elapsed      || 0,
                        };
                    }
                    this._fetchJobResult(sessionId);
                    this._es.close();
                    this._es = null;
                }

                if (event.type === "error") {
                    this.state.messages.push({ from: "bot", text: "❌ " + event.message });
                    this.state.loading = false;
                    this.state.currentStep = "";
                    this._es.close();
                    this._es = null;
                    this._scrollToBottom();
                }
            } catch (err) {
                console.error("SSE parse error:", err);
            }
        };

        this._es.onerror = () => {
            if (this._es) {
                this._es.close();
                this._es = null;
            }
            if (this.state.loading) {
                this._fetchJobResult(sessionId);
            }
        };
    }

    async _fetchJobResult(sessionId) {
        const MAX_RETRIES = 15;
        const DELAY_MS = 400;
        const jobId = this._currentJobId || "";

        let response = null;

        for (let i = 0; i < MAX_RETRIES; i++) {
            try {
                const result = await this.rpc("/dineflow/chat/result", {
                    session_id: sessionId,
                    job_id:     jobId,
                });

                if (result.response) {
                    response = result.response;
                    break;
                }
            } catch (e) {
                console.error("poll error:", e);
            }
            await new Promise(r => setTimeout(r, DELAY_MS));
        }

        let tokenText = null;
        if (this.state.lastTokenReport) {
            const t = this.state.lastTokenReport;
            tokenText = `📊 ${t.total} tokens · ${t.elapsed.toFixed(1)}s`;
        }

        this.state.messages.push({
            from:      "bot",
            text:      response || "Không có phản hồi.",
            tokenText: tokenText,
        });

        this._currentJobId = null;
        this.state.loading = false;
        this.state.currentStep = "";
        this.state.lastTokenReport = null;
        this._scrollToBottom();
    }

    onKeyDown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.sendMessage();
        }
    }

    _scrollToBottom() {
        setTimeout(() => {
            const el = this.messageEndRef.el;
            if (el) el.scrollIntoView({ behavior: "smooth" });
        }, 50);
    }
}

registry.category("actions").add("dineflow_ai_chat", AIChatComponent);