let socket = null;
let pending = null;

function connect() {
  if (socket) {
    return;
  }
  socket = new WebSocket("ws://127.0.0.1:49152");
  socket.onopen = () => {
    if (pending) {
      socket.send(JSON.stringify(pending));
      pending = null;
    }
  };
  socket.onclose = () => {
    socket = null;
    setTimeout(connect, 1000);
  };
  socket.onerror = () => {
    socket = null;
  };
}

function sendTab(tab) {
  if (!tab || !tab.url) {
    return;
  }
  const payload = {
    type: "tab_change",
    url: tab.url,
    title: tab.title || "",
    ts: Date.now() / 1000,
    browser: "chromium"
  };
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(payload));
  } else {
    pending = payload;
    connect();
  }
}

chrome.tabs.onActivated.addListener(async (activeInfo) => {
  const tab = await chrome.tabs.get(activeInfo.tabId);
  sendTab(tab);
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.active) {
    sendTab(tab);
  }
});

connect();
