import DOMPurify from 'dompurify';
import { marked } from 'marked';
import { useEffect, useState } from 'react';

interface MarkdownProps {
  content: string;
  className?: string;
}

/**
 * Markdown renderer component with XSS protection via DOMPurify
 */
export function Markdown({ content, className = '' }: MarkdownProps) {
  const [html, setHtml] = useState('');

  useEffect(() => {
    const renderMarkdown = async () => {
      // Configure marked
      marked.setOptions({
        breaks: true, // Convert \n to <br>
        gfm: true, // GitHub Flavored Markdown
      });

      // Convert markdown to HTML
      const rawHtml = await marked.parse(content);
      
      // Sanitize HTML to prevent XSS
      const cleanHtml = DOMPurify.sanitize(rawHtml, {
        ALLOWED_TAGS: [
          'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
          'ul', 'ol', 'li', 'blockquote', 'code', 'pre', 'a', 'hr', 'table',
          'thead', 'tbody', 'tr', 'th', 'td', 'del', 'ins'
        ],
        ALLOWED_ATTR: ['href', 'title', 'target', 'rel'],
      });

      setHtml(cleanHtml);
    };

    renderMarkdown();
  }, [content]);

  return (
    <div
      className={`prose prose-invert max-w-none selectable-text ${className}`}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

