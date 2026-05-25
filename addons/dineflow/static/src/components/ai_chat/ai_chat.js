/** @odoo-module **/
import { Component, useState, onMounted, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class AIChatComponent extends Component {
    static template = "dineflow.AIChatComponent";

    setup() {
        this.rpc = useService("rpc");
        this.messageEndRef = useRef("messageEnd");

        this.state = useState({
            messages: [],
            input: "",
            loading: false,
        });

        onMounted(() => this._loadHistory());
    }

    async _loadHistory() {
        const history = await this.rpc("/dineflow/chat/history", {});
        for (const h of history) {
            this.state.messages.push({ from: "user", text: h.message, time: h.created_at });
            this.state.messages.push({ from: "bot", text: h.response, time: h.created_at });
        }
        this._scrollToBottom();
    }

    async sendMessage() {
        const message = this.state.input.trim();
        if (!message || this.state.loading) return;

        this.state.messages.push({ from: "user", text: message });
        this.state.input = "";
        this.state.loading = true;
        this._scrollToBottom();

        try {
            const result = await this.rpc("/dineflow/chat", { message });
            this.state.messages.push({ from: "bot", text: result.response });
        } catch (e) {
            this.state.messages.push({ from: "bot", text: "Lỗi kết nối AI. Vui lòng thử lại." });
        } finally {
            this.state.loading = false;
            this._scrollToBottom();
        }
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