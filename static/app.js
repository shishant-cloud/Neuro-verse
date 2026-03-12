/* ═══════════════════════════════════════════════════════════════
   LaunchGate — static/js/app.js
   Social Hub (Socket.IO chat) + UI helpers
   Must match app.py field names exactly.
   ═══════════════════════════════════════════════════════════════ */

/* Globals injected by layout.html:
   const CURRENT_USER_ID  = <int>
   const CURRENT_USERNAME = "<str>"
*/

(function () {
  'use strict';

  /* ── Socket.IO ──────────────────────────────────────────────── */
  let socket          = null;
  let socketConnected = false;

  function initSocket() {
    if (socket) return;
    socket = io({ transports: ['websocket', 'polling'] });

    socket.on('connect', () => {
      socketConnected = true;
      socket.emit('user_online', {
        user_id:  CURRENT_USER_ID,
        username: CURRENT_USERNAME
      });
      refreshUserList();
    });

    socket.on('disconnect', () => { socketConnected = false; });

    socket.on('receive_message', (data) => {
      const fromMe = data.sender_id === CURRENT_USER_ID;
      if (
        activePeerId !== null &&
        (data.sender_id === activePeerId || (fromMe && data.receiver_id === activePeerId))
      ) {
        appendMessage(data);
        scrollBottom();
      }
      if (!fromMe) { bumpUnread(); shakeFab(); }
    });

    socket.on('user_joined', refreshUserList);
    socket.on('user_left',   refreshUserList);
  }

  /* ── Panel state ────────────────────────────────────────────── */
  let panelOpen      = false;
  let activePeerId   = null;
  let activePeerName = null;

  const elPanel    = document.getElementById('chatPanel');
  const elFab      = document.getElementById('chatFab');
  const elClose    = document.getElementById('chatClose');
  const elNavBtn   = document.getElementById('chatToggleBtn');
  const elSideLink = document.getElementById('chatToggleSidebar');
  const elInput    = document.getElementById('chatInput');
  const elSend     = document.getElementById('chatSend');
  const elMsgs     = document.getElementById('chatMessages');
  const elUserList = document.getElementById('chatUserList');
  const elMenu     = document.getElementById('menuToggle');
  const elSidebar  = document.getElementById('sidebar');

  /* ── Open / close ───────────────────────────────────────────── */
  function openPanel(targetUid) {
    if (!elPanel) return;
    panelOpen = true;
    elPanel.classList.add('open');
    initSocket();
    if (targetUid && targetUid !== activePeerId) selectPeer(targetUid, null);
    clearUnread();
  }

  function closePanel() {
    panelOpen = false;
    if (elPanel) elPanel.classList.remove('open');
  }

  function togglePanel(targetUid) {
    if (panelOpen && !targetUid) closePanel();
    else openPanel(targetUid || null);
  }

  window.chatToggle = togglePanel;

  if (elFab)      elFab.addEventListener('click',     () => togglePanel());
  if (elClose)    elClose.addEventListener('click',   closePanel);
  if (elNavBtn)   elNavBtn.addEventListener('click',  () => togglePanel());
  if (elSideLink) elSideLink.addEventListener('click', e => { e.preventDefault(); togglePanel(); });

  if (elMenu && elSidebar) {
    elMenu.addEventListener('click', () => elSidebar.classList.toggle('open'));
  }

  /* ── User list ──────────────────────────────────────────────── */
  async function refreshUserList() {
    try {
      const res  = await fetch('/api/users');
      const data = await res.json();
      renderUserList(data.users || data || []);
    } catch (e) { console.warn('[Chat] user list fetch failed', e); }
  }

  function renderUserList(users) {
    if (!elUserList) return;
    elUserList.innerHTML = `
      <div style="font-size:0.7rem;font-weight:700;color:var(--text-3);
                  text-transform:uppercase;letter-spacing:0.1em;padding:4px 8px 8px;">
        Users
      </div>`;

    if (!users.length) {
      elUserList.innerHTML += `
        <div style="padding:12px 8px;font-size:0.8rem;color:var(--text-3);text-align:center;">
          No other users found
        </div>`;
      return;
    }

    users.forEach(u => {
      const el = document.createElement('div');
      el.className     = 'chat-user-item' + (u.id === activePeerId ? ' active' : '');
      el.dataset.uid   = u.id;
      el.dataset.uname = u.username;
      el.innerHTML = `
        <div class="user-avatar" style="width:26px;height:26px;font-size:0.7rem;flex-shrink:0;">
          ${escHtml(u.username[0].toUpperCase())}
        </div>
        <span style="flex:1;">${escHtml(u.username)}</span>
        ${u.online ? '<div style="width:7px;height:7px;background:var(--accent-2);border-radius:50%;flex-shrink:0;"></div>' : ''}`;
      el.addEventListener('click', () => selectPeer(u.id, u.username));
      elUserList.appendChild(el);
    });
  }

  /* ── Select peer ────────────────────────────────────────────── */
  async function selectPeer(uid, uname) {
    activePeerId   = uid;
    activePeerName = uname;

    if (!activePeerName) {
      const el = elUserList && elUserList.querySelector(`[data-uid="${uid}"]`);
      if (el) activePeerName = el.dataset.uname;
    }

    if (elUserList) {
      elUserList.querySelectorAll('.chat-user-item').forEach(el => {
        el.classList.toggle('active', parseInt(el.dataset.uid) === uid);
      });
    }

    if (elInput) { elInput.disabled = false; elInput.placeholder = `Message ${activePeerName || ''}…`; }
    if (elSend)  elSend.disabled = false;

    if (elMsgs) elMsgs.innerHTML = `<div style="text-align:center;padding:16px;color:var(--text-3);font-size:0.78rem;">Loading…</div>`;

    await loadHistory(uid);
    scrollBottom();
  }

  /* ── Load history ───────────────────────────────────────────── */
  async function loadHistory(uid) {
    try {
      const res  = await fetch(`/api/messages/${uid}`);
      const data = await res.json();
      if (!elMsgs) return;
      elMsgs.innerHTML = '';

      const msgs = data.messages || data || [];
      if (!msgs.length) {
        elMsgs.innerHTML = `<div style="text-align:center;padding:28px;color:var(--text-3);font-size:0.82rem;">No messages yet. Say hello! 👋</div>`;
        return;
      }
      msgs.forEach(m => appendMessage(m, false));
    } catch (e) {
      console.warn('[Chat] history load failed', e);
      if (elMsgs) elMsgs.innerHTML = `<div style="text-align:center;padding:28px;color:var(--danger);font-size:0.82rem;">Could not load messages.</div>`;
    }
  }

  /* ── Append bubble ──────────────────────────────────────────── */
  function appendMessage(msg, doScroll = true) {
    if (!elMsgs) return;
    const isMine     = msg.sender_id === CURRENT_USER_ID;
    const senderName = msg.sender_username || msg.sender_name || activePeerName || '';
    let   timeStr    = '';
    if (msg.created_at) {
      try { timeStr = new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); }
      catch (_) {}
    }

    const wrap = document.createElement('div');
    wrap.className = 'chat-msg' + (isMine ? ' mine' : '');
    wrap.innerHTML = `
      ${!isMine ? `<div class="chat-meta">${escHtml(senderName)}</div>` : ''}
      <div class="chat-bubble">${escHtml(msg.content)}</div>
      ${timeStr ? `<div class="chat-meta">${timeStr}</div>` : ''}`;
    elMsgs.appendChild(wrap);
    if (doScroll) scrollBottom();
  }

  function scrollBottom() { if (elMsgs) elMsgs.scrollTop = elMsgs.scrollHeight; }

  /* ── Send ───────────────────────────────────────────────────── */
  async function sendMessage() {
    if (!elInput || activePeerId === null) return;
    const content = elInput.value.trim();
    if (!content) return;
    elInput.value = '';
    resizeTextarea(elInput);
    const now = new Date().toISOString();

    appendMessage({ sender_id: CURRENT_USER_ID, sender_username: CURRENT_USERNAME, receiver_id: activePeerId, content, created_at: now });

    try {
      const res  = await fetch('/api/messages/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recipient_id: activePeerId, content })
      });
      const data = await res.json();
      if (data.ok && socket && socketConnected) {
        socket.emit('send_message', {
          sender_id:       CURRENT_USER_ID,
          sender_username: CURRENT_USERNAME,
          recipient_id:    activePeerId,
          receiver_id:     activePeerId,
          content,
          created_at:      now
        });
      }
    } catch (e) { console.warn('[Chat] send failed', e); }
  }

  if (elSend)  elSend.addEventListener('click', sendMessage);
  if (elInput) {
    elInput.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } });
    elInput.addEventListener('input',   () => resizeTextarea(elInput));
  }

  /* ── Unread ─────────────────────────────────────────────────── */
  let unreadCount = 0;

  function bumpUnread()  { unreadCount++; applyUnreadBadges(); }
  function clearUnread() { unreadCount = 0; applyUnreadBadges(); }

  function applyUnreadBadges() {
    const has = unreadCount > 0;
    const navDot = document.querySelector('#chatToggleBtn .unread-badge');
    if (navDot) navDot.style.display = has ? 'block' : 'none';
    if (elFab)  elFab.classList.toggle('has-unread', has);
    const sideBadge = elSideLink && elSideLink.querySelector('.badge-red');
    if (sideBadge) { sideBadge.textContent = has ? String(unreadCount) : ''; sideBadge.style.display = has ? 'inline-flex' : 'none'; }
  }

  function shakeFab() {
    if (!elFab) return;
    elFab.style.transform = 'scale(1.22)';
    setTimeout(() => (elFab.style.transform = ''), 280);
  }

  /* ── Textarea resize ────────────────────────────────────────── */
  function resizeTextarea(el) { el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 120) + 'px'; }

  /* ── Flash auto-dismiss ─────────────────────────────────────── */
  const flashBox = document.getElementById('flashContainer');
  if (flashBox) {
    setTimeout(() => {
      [...flashBox.querySelectorAll('.flash')].forEach((f, i) => {
        setTimeout(() => {
          f.style.transition = 'opacity 0.4s, transform 0.4s';
          f.style.opacity    = '0';
          f.style.transform  = 'translateX(110%)';
          setTimeout(() => f.remove(), 420);
        }, i * 150);
      });
    }, 3500);
  }

  /* ── HTML escape ────────────────────────────────────────────── */
  function escHtml(s) {
    return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#039;');
  }

  /* ── Boot ───────────────────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', () => {
    initSocket();
    const uid = new URLSearchParams(window.location.search).get('chat');
    if (uid) openPanel(parseInt(uid));
  });

})();
