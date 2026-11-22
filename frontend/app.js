/* ─────────────────────────────────────────────
   RAG Studio — Application Logic
   API base: http://localhost:8000
   ───────────────────────────────────────────── */

const API = window.location.origin.startsWith('http') ? window.location.origin : 'http://localhost:8000';

// ── DOM refs ──────────────────────────────────
const uploadZone       = document.getElementById('uploadZone');
const fileInput        = document.getElementById('fileInput');
const browseBtn        = document.getElementById('browseBtn');
const uploadStatus     = document.getElementById('uploadStatus');
const statusFill       = document.getElementById('statusFill');
const statusText       = document.getElementById('statusText');
const fileList         = document.getElementById('fileList');
const refreshBtn       = document.getElementById('refreshBtn');
const chatWindow       = document.getElementById('chatWindow');
const welcomeState     = document.getElementById('welcomeState');
const chatInput        = document.getElementById('chatInput');
const sendBtn          = document.getElementById('sendBtn');
const sendLabel        = document.getElementById('sendLabel');
const sendSpinner      = document.getElementById('sendSpinner');
const clearBtn         = document.getElementById('clearBtn');
const toast            = document.getElementById('toast');
const sidebar          = document.getElementById('sidebar');
const menuToggle       = document.getElementById('menuToggle');
const sidebarCloseBtn  = document.getElementById('sidebarCloseBtn');
const sidebarBackdrop  = document.getElementById('sidebarBackdrop');

let toastTimer;

// ── Mobile Drawer Controller ──────────────────
function openSidebar() {
  if (sidebar) {
    sidebar.classList.add('open');
    sidebar.removeAttribute('aria-hidden');
  }
  if (sidebarBackdrop) sidebarBackdrop.classList.add('active');
  if (menuToggle) menuToggle.setAttribute('aria-expanded', 'true');
  if (sidebarCloseBtn) sidebarCloseBtn.focus();
}

function closeSidebar() {
  if (sidebar) {
    sidebar.classList.remove('open');
    sidebar.setAttribute('aria-hidden', 'true');
  }
  if (sidebarBackdrop) sidebarBackdrop.classList.remove('active');
  if (menuToggle) {
    menuToggle.setAttribute('aria-expanded', 'false');
    menuToggle.focus();
  }
}

if (menuToggle) menuToggle.addEventListener('click', openSidebar);
if (sidebarCloseBtn) sidebarCloseBtn.addEventListener('click', closeSidebar);
if (sidebarBackdrop) sidebarBackdrop.addEventListener('click', closeSidebar);

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeSidebar();
});

// ── Toast ─────────────────────────────────────
function showToast(msg, type = '') {
  clearTimeout(toastTimer);
  toast.textContent = msg;
  toast.className   = `toast show${type ? ' ' + type : ''}`;
  toastTimer = setTimeout(() => toast.classList.remove('show'), 3000);
}

// ── Auto-resize textarea ──────────────────────
chatInput.addEventListener('input', () => {
  chatInput.style.height = 'auto';
  chatInput.style.height = chatInput.scrollHeight + 'px';
});

// ── Send on Enter (Shift+Enter = newline) ─────
chatInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// ── File upload – drag & drop ─────────────────
uploadZone.addEventListener('dragover', e => {
  e.preventDefault();
  uploadZone.classList.add('drag-over');
});

uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));

uploadZone.addEventListener('drop', e => {
  e.preventDefault();
  uploadZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) uploadFile(file);
});

uploadZone.addEventListener('click', () => fileInput.click());
browseBtn.addEventListener('click', e => { e.stopPropagation(); fileInput.click(); });
fileInput.addEventListener('change', () => { if (fileInput.files[0]) uploadFile(fileInput.files[0]); });

// ── Upload a file ─────────────────────────────
async function uploadFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  // Show progress bar
  uploadStatus.hidden = false;
  statusText.textContent = 'Uploading…';
  animateFill(30);

  try {
    const res = await fetch(`${API}/file/upload`, { method: 'POST', body: formData });
    animateFill(80);

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    animateFill(100);
    statusText.textContent = 'Done!';
    showToast(`"${file.name}" uploaded successfully.`, 'success');
    fileInput.value = '';
    setTimeout(loadFiles, 600);
    if (window.innerWidth <= 768) {
      setTimeout(closeSidebar, 1000);
    }
  } catch (err) {
    statusText.textContent = 'Upload failed.';
    showToast(err.message, 'error');
  } finally {
    setTimeout(() => {
      uploadStatus.hidden = true;
      statusFill.style.width = '0%';
    }, 1200);
  }
}

function animateFill(pct) {
  statusFill.style.width = pct + '%';
}

// ── Load file list ────────────────────────────
async function loadFiles() {
  try {
    const res = await fetch(`${API}/file/show`);
    if (!res.ok) throw new Error();
    const data = await res.json();
    renderFiles(data.files || []);
  } catch {
    showToast('Could not load file list.', 'error');
  }
}

function renderFiles(files) {
  fileList.innerHTML = '';
  if (!files.length) {
    const placeholder = document.createElement('li');
    placeholder.className = 'file-item placeholder';
    placeholder.textContent = 'No files yet';
    fileList.appendChild(placeholder);
    return;
  }
  files.forEach(name => {
    const li = document.createElement('li');
    li.className = 'file-item';

    const icon = document.createElement('span');
    icon.className = 'file-icon';
    icon.textContent = '📄';

    const fileName = document.createElement('span');
    fileName.className = 'file-name';
    fileName.title = name;
    fileName.textContent = name;

    const delBtn = document.createElement('button');
    delBtn.className = 'delete-btn';
    delBtn.title = 'Delete';
    delBtn.setAttribute('aria-label', `Delete ${name}`);
    delBtn.textContent = '✕';
    delBtn.addEventListener('click', e => {
      e.stopPropagation();
      deleteFile(name);
    });

    li.append(icon, fileName, delBtn);
    fileList.appendChild(li);
  });
}

// ── Delete a file ─────────────────────────────
async function deleteFile(filename) {
  if (!confirm(`Delete "${filename}"?`)) return;
  try {
    const res = await fetch(`${API}/file/delete?filename=${encodeURIComponent(filename)}`, {
      method: 'DELETE'
    });
    if (!res.ok) throw new Error();
    showToast(`"${filename}" deleted.`);
    loadFiles();
  } catch {
    showToast('Delete failed.', 'error');
  }
}

refreshBtn.addEventListener('click', loadFiles);

// ── Send a chat message ───────────────────────
async function sendMessage() {
  const question = chatInput.value.trim();
  if (!question || sendBtn.disabled) return;

  // Hide welcome state
  welcomeState.style.display = 'none';

  appendBubble('user', question);
  chatInput.value = '';
  chatInput.style.height = 'auto';

  // Thinking indicator
  const typingRow = appendTyping();

  setSending(true);

  try {
    const res = await fetch(`${API}/chat/?prompt=${encodeURIComponent(question)}`, {
      method: 'POST'
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    const aiText = data?.data?.Ai || data?.Ai || '(no response)';
    const sources = data?.data?.sources || data?.sources || [];
    typingRow.remove();
    appendBubble('ai', aiText, sources);
  } catch (err) {
    typingRow.remove();
    appendBubble('ai', `⚠️ ${err.message}`);
  } finally {
    setSending(false);
  }
}

sendBtn.addEventListener('click', sendMessage);

// ── Helpers ───────────────────────────────────
function setSending(active) {
  sendBtn.disabled = active;
  sendBtn.setAttribute('aria-busy', active ? 'true' : 'false');
  sendLabel.hidden = active;
  sendSpinner.hidden = !active;
}

function appendBubble(role, text, sources = []) {
  const isUser = role === 'user';
  const row = document.createElement('div');
  row.className = `message-row ${isUser ? 'user' : 'ai'}`;
  row.innerHTML = `<div class="avatar ${isUser ? 'usr' : 'ai'}">${isUser ? '🧑' : '🤖'}</div>`;
  const bubble = document.createElement('div');
  bubble.className = `bubble ${isUser ? 'user' : 'ai'}`;
  if (isUser) {
    bubble.textContent = text;
  } else {
    renderMarkdown(bubble, text);

    if (Array.isArray(sources) && sources.length > 0) {
      const details = document.createElement('details');
      details.className = 'sources-accordion';

      const summary = document.createElement('summary');
      summary.className = 'sources-summary';
      summary.textContent = `📚 Sources (${sources.length})`;
      details.appendChild(summary);

      const list = document.createElement('div');
      list.className = 'sources-list';

      sources.forEach(src => {
        const card = document.createElement('div');
        card.className = 'source-card';

        const header = document.createElement('div');
        header.className = 'source-card-header';

        const titleRow = document.createElement('div');
        titleRow.className = 'source-title-row';

        const rankBadge = document.createElement('span');
        rankBadge.className = 'source-rank-badge';
        rankBadge.textContent = `#${src.rank || '1'}`;
        titleRow.appendChild(rankBadge);

        const filename = document.createElement('span');
        filename.className = 'source-filename';
        const sourceName = src.metadata?.source || src.metadata?.filename || src.id || 'Document Chunk';
        filename.textContent = sourceName;
        filename.title = sourceName;
        titleRow.appendChild(filename);

        header.appendChild(titleRow);

        const scoreBadge = document.createElement('span');
        scoreBadge.className = 'source-score-badge';
        const scoreVal = src.score ?? src.rerank_score ?? src.similarity_score;
        scoreBadge.textContent = scoreVal != null ? `Score: ${Number(scoreVal).toFixed(3)}` : 'Relevant';
        header.appendChild(scoreBadge);

        card.appendChild(header);

        const metaParts = [];
        if (src.metadata?.page != null) metaParts.push(`Page ${Number(src.metadata.page) + 1}`);
        if (src.metadata?.doc_index != null) metaParts.push(`Chunk #${src.metadata.doc_index}`);
        if (src.metadata?.content_length != null) metaParts.push(`${src.metadata.content_length} chars`);

        if (metaParts.length > 0) {
          const meta = document.createElement('div');
          meta.className = 'source-meta';
          meta.textContent = metaParts.join(' • ');
          card.appendChild(meta);
        }

        list.appendChild(card);
      });

      details.appendChild(list);
      bubble.appendChild(details);
    }
  }
  row.appendChild(bubble);
  chatWindow.appendChild(row);
  scrollToBottom();
  return row;
}

function renderMarkdown(container, markdown) {
  const lines = String(markdown ?? '').replace(/\r\n?/g, '\n').split('\n');
  const fragment = document.createDocumentFragment();

  for (let i = 0; i < lines.length;) {
    const line = lines[i];
    if (!line.trim()) {
      i++;
      continue;
    }

    if (isMarkdownTable(lines, i)) {
      const headers = splitMarkdownTableRow(line);
      const alignments = splitMarkdownTableRow(lines[i + 1]).map(cell => {
        if (cell.startsWith(':') && cell.endsWith(':')) return 'center';
        if (cell.endsWith(':')) return 'right';
        return 'left';
      });
      const wrapper = document.createElement('div');
      wrapper.className = 'markdown-table-scroll';
      wrapper.setAttribute('role', 'region');
      wrapper.setAttribute('aria-label', 'Scrollable data table');
      wrapper.tabIndex = 0;
      const table = document.createElement('table');
      table.className = 'markdown-table';
      const thead = document.createElement('thead');
      const headerRow = document.createElement('tr');

      headers.forEach((value, column) => {
        const cell = document.createElement('th');
        cell.scope = 'col';
        cell.style.textAlign = alignments[column] || 'left';
        appendInlineMarkdown(cell, value);
        headerRow.appendChild(cell);
      });
      thead.appendChild(headerRow);
      table.appendChild(thead);

      const tbody = document.createElement('tbody');
      i += 2;
      while (i < lines.length && lines[i].trim() && lines[i].includes('|')) {
        const values = splitMarkdownTableRow(lines[i]);
        const row = document.createElement('tr');
        headers.forEach((_, column) => {
          const cell = document.createElement('td');
          cell.style.textAlign = alignments[column] || 'left';
          appendInlineMarkdown(cell, values[column] || '');
          row.appendChild(cell);
        });
        tbody.appendChild(row);
        i++;
      }
      table.appendChild(tbody);
      wrapper.appendChild(table);
      fragment.appendChild(wrapper);
      continue;
    }

    const fence = line.match(/^ {0,3}(`{3,}|~{3,})/);
    if (fence) {
      const codeLines = [];
      const closeFence = new RegExp(`^ {0,3}${fence[1][0]}{${fence[1].length},}\\s*$`);
      i++;
      while (i < lines.length && !closeFence.test(lines[i])) codeLines.push(lines[i++]);
      if (i < lines.length) i++;

      const pre = document.createElement('pre');
      const code = document.createElement('code');
      code.textContent = codeLines.join('\n');
      pre.appendChild(code);
      fragment.appendChild(pre);
      continue;
    }

    const heading = line.match(/^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$/);
    if (heading) {
      const element = document.createElement(`h${heading[1].length}`);
      appendInlineMarkdown(element, heading[2]);
      fragment.appendChild(element);
      i++;
      continue;
    }

    if (/^ {0,3}(?:(?:\*\s*){3,}|(?:-\s*){3,}|(?:_\s*){3,})$/.test(line)) {
      fragment.appendChild(document.createElement('hr'));
      i++;
      continue;
    }

    if (/^ {0,3}>/.test(line)) {
      const quoteLines = [];
      while (i < lines.length && /^ {0,3}>/.test(lines[i])) {
        quoteLines.push(lines[i++].replace(/^ {0,3}> ?/, ''));
      }
      const quote = document.createElement('blockquote');
      renderMarkdown(quote, quoteLines.join('\n'));
      fragment.appendChild(quote);
      continue;
    }

    const listItem = line.match(/^ {0,3}([-+*]|\d+[.)])\s+(.*)$/);
    if (listItem) {
      const ordered = /^\d/.test(listItem[1]);
      const list = document.createElement(ordered ? 'ol' : 'ul');
      while (i < lines.length) {
        const item = lines[i].match(/^ {0,3}([-+*]|\d+[.)])\s+(.*)$/);
        if (!item || /^\d/.test(item[1]) !== ordered) break;
        const li = document.createElement('li');
        appendInlineMarkdown(li, item[2]);
        list.appendChild(li);
        i++;
      }
      fragment.appendChild(list);
      continue;
    }

    const paragraphLines = [line];
    i++;
    while (i < lines.length && lines[i].trim() && !isMarkdownBlock(lines[i], lines, i)) {
      paragraphLines.push(lines[i++]);
    }
    const paragraph = document.createElement('p');
    appendInlineMarkdown(paragraph, paragraphLines.join(' '));
    fragment.appendChild(paragraph);
  }

  container.replaceChildren(fragment);
}

function isMarkdownBlock(line, lines, index) {
  return isMarkdownTable(lines, index)
    || /^ {0,3}(?:`{3,}|~{3,}|#{1,6}\s+|>|[-+*]\s+|\d+[.)]\s+)/.test(line)
    || /^ {0,3}(?:(?:\*\s*){3,}|(?:-\s*){3,}|(?:_\s*){3,})$/.test(line);
}

function isMarkdownTable(lines, index) {
  if (!lines[index] || !lines[index].includes('|') || !lines[index + 1]) return false;
  const cells = splitMarkdownTableRow(lines[index + 1]);
  return cells.length > 1 && cells.every(cell => /^:?-{3,}:?$/.test(cell));
}

function splitMarkdownTableRow(line) {
  const source = line.trim().replace(/^\|/, '').replace(/\|$/, '');
  const cells = [];
  let cell = '';
  for (let i = 0; i < source.length; i++) {
    if (source[i] === '\\' && source[i + 1] === '|') {
      cell += '|';
      i++;
    } else if (source[i] === '|') {
      cells.push(cell.trim());
      cell = '';
    } else {
      cell += source[i];
    }
  }
  cells.push(cell.trim());
  return cells;
}

function appendInlineMarkdown(parent, text, depth = 0) {
  if (depth > 8) {
    parent.appendChild(document.createTextNode(text));
    return;
  }

  const appendNested = (element, value) => appendInlineMarkdown(element, value, depth + 1);
  const delimiters = [
    { token: '**', tag: 'strong' },
    { token: '__', tag: 'strong' },
    { token: '~~', tag: 'del' },
    { token: '*', tag: 'em' },
    { token: '_', tag: 'em' }
  ];
  let index = 0;
  let plain = '';
  const flush = () => {
    if (plain) parent.appendChild(document.createTextNode(plain));
    plain = '';
  };

  while (index < text.length) {
    if (text[index] === '\n') {
      flush();
      parent.appendChild(document.createElement('br'));
      index++;
      continue;
    }

    const lineBreak = text.slice(index).match(/^<br\s*\/?>/i);
    if (lineBreak) {
      flush();
      parent.appendChild(document.createElement('br'));
      index += lineBreak[0].length;
      continue;
    }

    if (text[index] === '`') {
      const marker = text.slice(index).match(/^`+/)[0];
      const end = findCodeSpanEnd(text, marker, index + marker.length);
      if (end !== -1) {
        flush();
        const code = document.createElement('code');
        code.textContent = text.slice(index + marker.length, end).replace(/\n/g, ' ');
        parent.appendChild(code);
        index = end + marker.length;
        continue;
      }
    }

    if (text[index] === '[') {
      const link = text.slice(index).match(/^\[([^\]]+)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)/);
      if (link) {
        let url;
        try {
          url = new URL(link[2], window.location.href);
        } catch {
          url = null;
        }
        if (url && ['http:', 'https:', 'mailto:'].includes(url.protocol)) {
          flush();
          const anchor = document.createElement('a');
          anchor.href = url.href;
          anchor.rel = 'noopener noreferrer';
          anchor.target = '_blank';
          if (link[3]) anchor.title = link[3];
          appendNested(anchor, link[1]);
          parent.appendChild(anchor);
          index += link[0].length;
          continue;
        }
      }
    }

    const matchedDelimiter = delimiters.find(({ token }) => text.startsWith(token, index));
    if (matchedDelimiter) {
      const isUnderscore = matchedDelimiter.token.startsWith('_');
      const previousCharacter = text[index - 1] || '';
      const nextCharacter = text[index + matchedDelimiter.token.length] || '';
      const intrawordStart = isUnderscore
        && (/[A-Za-z0-9]/.test(previousCharacter) || /\s/.test(nextCharacter));
      const end = intrawordStart
        ? -1
        : findInlineDelimiterEnd(text, matchedDelimiter.token, index + matchedDelimiter.token.length);
      if (end > index + matchedDelimiter.token.length) {
        flush();
        const element = document.createElement(matchedDelimiter.tag);
        appendNested(element, text.slice(index + matchedDelimiter.token.length, end));
        parent.appendChild(element);
        index = end + matchedDelimiter.token.length;
        continue;
      }
    }

    plain += text[index++];
  }
  flush();
}

function findCodeSpanEnd(text, marker, from) {
  let end = text.indexOf('`', from);
  while (end !== -1) {
    const run = text.slice(end).match(/^`+/)[0];
    if (run.length === marker.length) return end;
    end = text.indexOf('`', end + run.length);
  }
  return -1;
}

function findInlineDelimiterEnd(text, token, from) {
  let end = text.indexOf(token, from);
  while (end !== -1) {
    const nextCharacter = text[end + token.length] || '';
    if (!token.startsWith('_') || !/[A-Za-z0-9]/.test(nextCharacter)) return end;
    end = text.indexOf(token, end + token.length);
  }
  return -1;
}

function appendTyping() {
  const row = document.createElement('div');
  row.className = 'message-row ai';
  row.innerHTML = `
    <div class="avatar ai">🤖</div>
    <div class="bubble ai typing-bubble">
      <span></span><span></span><span></span>
    </div>
  `;
  chatWindow.appendChild(row);
  scrollToBottom();
  return row;
}

function scrollToBottom() {
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

// ── Clear chat ────────────────────────────────
clearBtn.addEventListener('click', () => {
  // Remove all message rows, keep welcome state
  chatWindow.querySelectorAll('.message-row').forEach(el => el.remove());
  welcomeState.style.display = '';
});

// ── Init ──────────────────────────────────────
loadFiles();

