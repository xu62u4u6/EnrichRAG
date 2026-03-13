window.enrichRAGUI = (() => {
  const ALLOWED_TAGS = new Set([
    'A', 'B', 'BLOCKQUOTE', 'BR', 'CODE', 'EM', 'H1', 'H2', 'H3', 'H4',
    'HR', 'I', 'LI', 'OL', 'P', 'PRE', 'STRONG', 'UL',
  ]);
  const ALLOWED_ATTRS = {
    A: new Set(['href', 'target', 'rel']),
  };
  const SAFE_URL_PROTOCOLS = new Set(['http:', 'https:', 'mailto:']);

  function esc(value) {
    const div = document.createElement('div');
    div.textContent = value == null ? '' : String(value);
    return div.innerHTML;
  }

  function escAttr(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/'/g, '&#39;')
      .replace(/"/g, '&quot;');
  }

  function safeUrl(url) {
    if (!url) return '#';
    try {
      const parsed = new URL(url, window.location.origin);
      if (!SAFE_URL_PROTOCOLS.has(parsed.protocol)) return '#';
      return parsed.href;
    } catch {
      return '#';
    }
  }

  function sanitizeNode(node) {
    if (node.nodeType === Node.TEXT_NODE) return;
    if (node.nodeType !== Node.ELEMENT_NODE) {
      node.remove();
      return;
    }

    if (!ALLOWED_TAGS.has(node.tagName)) {
      const fragment = document.createDocumentFragment();
      while (node.firstChild) fragment.appendChild(node.firstChild);
      node.replaceWith(fragment);
      return;
    }

    Array.from(node.attributes).forEach((attr) => {
      const allowed = ALLOWED_ATTRS[node.tagName];
      const name = attr.name.toLowerCase();
      if (!allowed || !allowed.has(attr.name)) {
        node.removeAttribute(attr.name);
        return;
      }
      if (node.tagName === 'A' && name === 'href') {
        node.setAttribute('href', safeUrl(attr.value));
      }
    });

    if (node.tagName === 'A') {
      node.setAttribute('target', '_blank');
      node.setAttribute('rel', 'noopener noreferrer');
    }

    Array.from(node.childNodes).forEach(sanitizeNode);
  }

  function renderMarkdownSafe(markdown) {
    const template = document.createElement('template');
    template.innerHTML = marked.parse(markdown || '');
    Array.from(template.content.childNodes).forEach(sanitizeNode);
    return template.innerHTML;
  }

  function renderStateCard({
    tone = 'empty',
    icon = 'inbox',
    title = '',
    description = '',
    compact = false,
  } = {}) {
    const titleHtml = title ? `<h3>${esc(title)}</h3>` : '';
    const descHtml = description ? `<p>${esc(description)}</p>` : '';
    return `
      <div class="state-card state-card-${escAttr(tone)}${compact ? ' state-card-compact' : ''}">
        <div class="state-card-icon"><i data-lucide="${escAttr(icon)}"></i></div>
        ${titleHtml}
        ${descHtml}
      </div>`;
  }

  return {
    esc,
    escAttr,
    renderMarkdownSafe,
    renderStateCard,
    safeUrl,
  };
})();
