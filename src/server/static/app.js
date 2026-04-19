// 实时画面：WS 收 JPEG 二进制 → blob URL → <img>
// 事件：先 REST 拉取历史，再 WS 订阅新事件

const streamImg = document.getElementById("stream");
const placeholder = document.getElementById("stream-placeholder");
const statusEl = document.getElementById("conn-status");
const eventsEl = document.getElementById("events");
const refreshBtn = document.getElementById("refresh-btn");

let lastBlobUrl = null;

function setStatus(ok) {
    statusEl.textContent = ok ? "已连接" : "未连接";
    statusEl.classList.toggle("connected", ok);
    statusEl.classList.toggle("disconnected", !ok);
}

function connectStream() {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${proto}//${location.host}/ws/stream`);
    ws.binaryType = "arraybuffer";

    ws.onopen = () => setStatus(true);
    ws.onclose = () => {
        setStatus(false);
        setTimeout(connectStream, 2000);
    };
    ws.onerror = () => ws.close();
    ws.onmessage = (ev) => {
        const blob = new Blob([ev.data], { type: "image/jpeg" });
        const url = URL.createObjectURL(blob);
        if (lastBlobUrl) URL.revokeObjectURL(lastBlobUrl);
        lastBlobUrl = url;
        streamImg.src = url;
        streamImg.classList.add("active");
        placeholder.style.display = "none";
    };
}

function connectEvents() {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${proto}//${location.host}/ws/events`);
    ws.onmessage = (ev) => {
        const event = JSON.parse(ev.data);
        prependEvent(event, true);
    };
    ws.onclose = () => setTimeout(connectEvents, 2000);
}

function fmtTime(ts) {
    if (!ts) return "";
    return new Date(ts).toLocaleString();
}

function renderEvent(ev) {
    const li = document.createElement("li");
    const meta = ev.metadata || {};
    li.innerHTML = `
        <div class="ts">${fmtTime(ev.timestamp)}</div>
        <div class="desc">[${ev.event_type}] ${ev.description}</div>
        <div class="meta">${meta.label ? `物体: ${meta.label}` : ""}${meta.track_id !== undefined ? ` · #${meta.track_id}` : ""}</div>
    `;
    return li;
}

function prependEvent(ev, fresh = false) {
    const li = renderEvent(ev);
    if (fresh) li.classList.add("fresh");
    eventsEl.prepend(li);
    // 限制 DOM 大小
    while (eventsEl.children.length > 200) {
        eventsEl.removeChild(eventsEl.lastChild);
    }
}

async function loadHistory() {
    eventsEl.innerHTML = "";
    try {
        const res = await fetch("/api/events?limit=50");
        const data = await res.json();
        for (const ev of data.events) {
            eventsEl.appendChild(renderEvent(ev));
        }
    } catch (err) {
        console.error("加载历史失败", err);
    }
}

refreshBtn.addEventListener("click", loadHistory);

loadHistory();
connectStream();
connectEvents();
