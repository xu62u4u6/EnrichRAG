import { marked } from 'marked';

const allowedTags = new Set(['A', 'B', 'BLOCKQUOTE', 'BR', 'CODE', 'EM', 'H1', 'H2', 'H3', 'H4', 'HR', 'I', 'LI', 'OL', 'P', 'PRE', 'STRONG', 'UL']);
const allowedAttrs: Record<string, Set<string>> = {
  A: new Set(['href', 'target', 'rel']),
};

function sanitizeNode(node: ChildNode) {
  if (node.nodeType === Node.TEXT_NODE) return;
  if (node.nodeType !== Node.ELEMENT_NODE) {
    node.remove();
    return;
  }

  const element = node as HTMLElement;
  if (!allowedTags.has(element.tagName)) {
    const fragment = document.createDocumentFragment();
    while (element.firstChild) fragment.appendChild(element.firstChild);
    element.replaceWith(fragment);
    return;
  }

  Array.from(element.attributes).forEach((attr) => {
    const allowed = allowedAttrs[element.tagName];
    if (!allowed || !allowed.has(attr.name)) {
      element.removeAttribute(attr.name);
      return;
    }
    if (element.tagName === 'A' && attr.name === 'href') {
      try {
        const parsed = new URL(attr.value, window.location.origin);
        if (!['http:', 'https:', 'mailto:'].includes(parsed.protocol)) {
          element.setAttribute('href', '#');
        } else {
          element.setAttribute('href', parsed.href);
        }
      } catch {
        element.setAttribute('href', '#');
      }
    }
  });

  if (element.tagName === 'A') {
    element.setAttribute('target', '_blank');
    element.setAttribute('rel', 'noopener noreferrer');
  }

  Array.from(element.childNodes).forEach(sanitizeNode);
}

export function renderMarkdownSafe(markdown: string) {
  const template = document.createElement('template');
  template.innerHTML = marked.parse(markdown || '') as string;
  Array.from(template.content.childNodes).forEach(sanitizeNode);
  return template.innerHTML;
}
