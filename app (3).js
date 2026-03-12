/* ═══════════════════════════════════════════════════════════════════════
   NeuroVerse — static/js/app.js
   Social Hub: Socket.IO real-time chat + user list + unread badges
   -----------------------------------------------------------------------
   Requires:
     - Socket.IO 4.x loaded BEFORE this file
     - CURRENT_USER_ID  (integer)  injected in layout.html
     - CURRENT_USERNAME (string)   injected in layout.html
   ═══════════════════════════════════════════════════════════════════════ */

'use strict';

/* ── 1. Socket.IO connection ──────────────────────────────────────────── */
const socket = io({ transports: ['websocket', 'polling'] });

let activePeerId   = null;   // currently open conversation
let unreadInterval = null;   // polling interval for unread count

/* ── 2. Socket events ─────────────────────────────────────────────────── */
socket.on('connect', () => {
  socket.emit('user_online', {
    user_id:  CURRENT_USER_ID,
    username: CURRENT_USERNAME
  });
});

/* Real-time incoming message */
socket.on('receive_message', (msg) => {
  const isChatOpen = document.getElementById('chatPanel')?.classList.contains('open');

  // If the message belongs to the active conversation — render it immediately
  if (msg.sender_id === activePeerId || msg.receiver_id === activePeerId) {
    appendMessage({
      sender_id:       msg.sender_id,
      sender_username: msg.sender_username,
      content:         msg.content,
      created_at:      msg.created_at
    });
  }

  // Update unread dot on FAB if panel is closed or different chat is open
  if (!isChatOpen || msg.sender_id !== activePeerId) {
    refreshUnreadBadge();
    // Highlight the sender row in the user list
    const senderRow = document.querySelector(`.chat-user-item[data-uid="${msg.sender_id}"]`);
    if (senderRow && !senderRow.classList.contains('active')) {
      senderRow.classList.add('has-unread');
      const dot = senderRow.querySelector('.user-unread-dot');
      if (dot) dot.style.display = 'block';
    }
  }
});

/* Someone came online — update their indicator */
socket.on('user_joined', (data) => {
  const row = document.querySelector(`.chat-user-item[data-uid="${data.user_id}"]`);
  if (row) {
    const statusDot = row.querySelector('.online-dot');
    if (statusDot) statusDot.classList.add('online');
  }
});

/* Someone went offline */
socket.on('user_left', (data) => {
  const row = document.querySelector(`.chat-user-item[data-uid="${data.user_id}"]`);
  if (row) {
    const statusDot = row.querySelector('.online-dot');
    if (statusDot) statusDot.classList.remove('online');
  }
});


/* ── 3. Panel open / close ────────────────────────────────────────────── */
window.chatToggle = function (openWithUserId) {
  const panel = document.getElementById('chatPanel');
  if (!panel) return;

  const isOpen = panel.classList.contains('open');

  if (isOpen && !openWithUserId) {
    panel.classList.remove('open');
    return;
  }

  panel.classList.add('open');
  loadUsers().then(() => {
    if (openWithUserId) openConversation(openWithUserId);
  });
};


/* ── 4. Load user list ────────────────────────────────────────────────── */
async function loadUsers() {
  const list = document.getElementById('chatUserList');
  if (!list) return;

  try {
    const res   = await fetch('/api/users');
    const data  = await res.json();
    const users = data.users || [];

    if (users.length === 0) {
      list.innerHTML = `
        <div style="font-size:0.7rem;font-weight:700;color:var(--text-3);
                    text-transform:uppercase;letter-spacing:0.1em;
                    padding:12px 16px 8px;">Online Teammates</div>
        <div style="padding:20px 16px;font-size:0.82rem;color:var(--text-4);text-align:center;">
          No other users yet.
        </div>`;
      return;
    }

    list.innerHTML = `
      <div style="font-size:0.7rem;font-weight:700;color:var(--text-3);
                  text-transform:uppercase;letter-spacing:0.1em;
                  padding:12px 16px 8px;">Online Teammates</div>
      ${users.map(u => `
        <div class="chat-user-item ${u.id === activePeerId ? 'active' : ''}"
             data-uid="${u.id}"
             onclick="openConversation(${u.id})"
             title="Chat with ${escapeHtml(u.username)}">
          <div style="position:relative;flex-shrink:0;">
            <div class="user-avatar" style="width:30px;height:30px;font-size:0.72rem;">
              ${escapeHtml(u.username[0].toUpperCase())}
            </div>
            <span class="online-dot" style="
              position:absolute;bottom:0;right:0;
              width:8px;height:8px;border-radius:50%;
              background:var(--accent-2);
              border:2px solid var(--bg-raised);
              display:block;"></span>
          </div>
          <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
            ${escapeHtml(u.username)}
          </span>
          <span class="user-unread-dot" style="
            width:8px;height:8px;border-radius:50%;
            background:var(--danger);display:none;flex-shrink:0;"></span>
        </div>
      `).join('')}`;
  } catch (err) {
    console.error('[SocialHub] loadUsers failed:', err);
  }
}


/* ── 5. Open a conversation ───────────────────────────────────────────── */
window.openConversation = async function (peerId) {
  peerId = parseInt(peerId, 10);
  activePeerId = peerId;

  // Update active state in user list
  document.querySelectorAll('.chat-user-item').forEach(el => {
    el.classList.toggle('active', parseInt(el.dataset.uid, 10) === peerId);
  });

  // Clear unread dot for this user
  const peerRow = document.querySelector(`.chat-user-item[data-uid="${peerId}"]`);
  if (peerRow) {
    peerRow.classList.remove('has-unread');
    const dot = peerRow.querySelector('.user-unread-dot');
    if (dot) dot.style.display = 'none';
  }

  // Enable input
  const input  = document.getElementById('chatInput');
  const sendBtn = document.getElementById('chatSend');
  if (input)   { input.disabled  = false; input.focus(); }
  if (sendBtn) { sendBtn.disabled = false; }

  // Show loading state
  const box = document.getElementById('chatMessages');
  if (box) {
    box.innerHTML = `
      <div style="text-align:center;padding:40px 20px;color:var(--text-3);font-size:0.83rem;">
        <div style="font-size:1.4rem;margin-bottom:10px;">⏳</div>
        Loading messages…
      </div>`;
  }

  try {
    const res  = await fetch(`/api/messages/${peerId}`);
    const data = await res.json();
    renderMessages(data.messages || []);
  } catch (err) {
    console.error('[SocialHub] openConversation failed:', err);
    if (box) box.innerHTML = `<div style="padding:20px;color:var(--danger);font-size:0.83rem;">Failed to load messages.</div>`;
  }

  // Refresh global unread count
  refreshUnreadBadge();
};


/* ── 6. Render message history ────────────────────────────────────────── */
function renderMessages(msgs) {
  const box = document.getElementById('chatMessages');
  if (!box) return;

  if (msgs.length === 0) {
    box.innerHTML = `
      <div style="text-align:center;padding:40px 20px;color:var(--text-3);font-size:0.83rem;">
        <div style="font-size:2rem;margin-bottom:10px;">👋</div>
        No messages yet. Say hello!
      </div>`;
    return;
  }

  box.innerHTML = msgs.map(m => buildBubble(m)).join('');
  box.scrollTop = box.scrollHeight;
}


/* ── 7. Append a single new bubble ───────────────────────────────────── */
function appendMessage(m) {
  const box = document.getElementById('chatMessages');
  if (!box) return;

  // Remove empty-state placeholder if present
  const placeholder = box.querySelector('[data-placeholder]');
  if (placeholder) placeholder.remove();
  const emptyDiv = box.querySelector('div[style*="text-align:center"]');
  if (emptyDiv && box.children.length === 1) emptyDiv.remove();

  box.insertAdjacentHTML('beforeend', buildBubble(m));
  box.scrollTop = box.scrollHeight;
}


/* ── 8. Build a chat bubble HTML string ──────────────────────────────── */
function buildBubble(m) {
  const isMine = m.sender_id === CURRENT_USER_ID;
  const time   = formatTime(m.created_at);

  return `
    <div class="chat-msg ${isMine ? 'mine' : 'theirs'}">
      <div class="chat-bubble">${escapeHtml(m.content)}</div>
      <div class="chat-meta">${isMine ? 'You' : escapeHtml(m.sender_username)} · ${time}</div>
    </div>`;
}


/* ── 9. Send message ──────────────────────────────────────────────────── */
async function sendMessage() {
  const input   = document.getElementById('chatInput');
  const content = input?.value.trim();
  if (!content || !activePeerId) return;

  const now = new Date().toISOString();

  // Optimistically render your own bubble immediately
  appendMessage({
    sender_id:       CURRENT_USER_ID,
    sender_username: CURRENT_USERNAME,
    content,
    created_at:      now
  });

  input.value = '';
  input.style.height = 'auto';

  try {
    // 1. Persist to DB
    await fetch('/api/messages/send', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ recipient_id: activePeerId, content })
    });

    // 2. Broadcast to recipient via Socket.IO
    socket.emit('send_message', {
      sender_id:       CURRENT_USER_ID,
      sender_username: CURRENT_USERNAME,
      recipient_id:    activePeerId,
      content,
      created_at:      now
    });
  } catch (err) {
    console.error('[SocialHub] sendMessage failed:', err);
  }
}


/* ── 10. Unread badge refresh ────────────────────────────────────────── */
async function refreshUnreadBadge() {
  try {
    const res  = await fetch('/api/unread');
    const data = await res.json();
    const count = data.unread || 0;

    // FAB dot
    const fab = document.getElementById('chatFab');
    if (fab) fab.classList.toggle('has-unread', count > 0);

    // Navbar badge (if you have one with id="navUnreadBadge")
    const navBadge = document.getElementById('navUnreadBadge');
    if (navBadge) {
      navBadge.textContent = count > 99 ? '99+' : count;
      navBadge.style.display = count > 0 ? 'flex' : 'none';
    }
  } catch (_) { /* silent fail */ }
}


/* ── 11. Auto-grow textarea ──────────────────────────────────────────── */
function autoGrow(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}


/* ── 12. Helpers ─────────────────────────────────────────────────────── */
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function formatTime(isoString) {
  if (!isoString) return '';
  try {
    const d = new Date(isoString);
    const now = new Date();
    const isToday = d.toDateString() === now.toDateString();
    if (isToday) {
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
           + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch (_) { return ''; }
}


/* ── 13. Wire up DOM events ───────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {

  /* FAB open button */
  document.getElementById('chatFab')
    ?.addEventListener('click', () => window.chatToggle());

  /* Close button inside panel */
  document.getElementById('chatClose')
    ?.addEventListener('click', () => window.chatToggle());

  /* Send button */
  document.getElementById('chatSend')
    ?.addEventListener('click', sendMessage);

  /* Enter to send, Shift+Enter for newline */
  document.getElementById('chatInput')
    ?.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

  /* Auto-grow textarea */
  document.getElementById('chatInput')
    ?.addEventListener('input', function () { autoGrow(this); });

  /* Poll unread count every 15 seconds as a fallback */
  refreshUnreadBadge();
  unreadInterval = setInterval(refreshUnreadBadge, 15_000);

});
