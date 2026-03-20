import DOMPurify from 'dompurify';
import { marked } from 'marked';

// Allow standard Markdown tags + tables
const ALLOWED_TAGS = [
  'a', 'b', 'blockquote', 'br', 'code', 'em', 'h1', 'h2', 'h3', 'h4',
  'hr', 'i', 'li', 'ol', 'p', 'pre', 'strong', 'ul',
  'table', 'thead', 'tbody', 'tr', 'th', 'td',
];

const ALLOWED_ATTR = ['href', 'target', 'rel'];

// Force all links to open in new tab safely
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    node.setAttribute('target', '_blank');
    node.setAttribute('rel', 'noopener noreferrer');
  }
});

export function renderMarkdownSafe(markdown: string) {
  const raw = marked.parse(markdown || '') as string;
  return DOMPurify.sanitize(raw, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    ALLOW_DATA_ATTR: false,
  });
}
