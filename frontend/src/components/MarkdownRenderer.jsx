import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';

// Custom CSS for Claude-like clean markdown styling
const markdownStyles = `
  .markdown-content {
    line-height: 1.7;
    color: hsl(var(--foreground));
  }
  
  .markdown-content > * {
    margin-bottom: 0;
  }
  
  .markdown-content > * + * {
    margin-top: 1.25em;
  }
  
  .markdown-content > * + h1,
  .markdown-content > * + h2 {
    margin-top: 2.5em;
  }
  
  .markdown-content > * + h3 {
    margin-top: 2em;
  }
  
  .markdown-content > * + h4,
  .markdown-content > * + h5,
  .markdown-content > * + h6 {
    margin-top: 1.75em;
  }
  
  .markdown-content h1 {
    font-size: 1.5em;
    font-weight: 600;
    line-height: 1.3;
    margin-top: 2em;
    margin-bottom: 0.75em;
  }
  
  .markdown-content h2 {
    font-size: 1.25em;
    font-weight: 600;
    line-height: 1.3;
    margin-top: 2em;
    margin-bottom: 0.75em;
  }
  
  .markdown-content h3 {
    font-size: 1.125em;
    font-weight: 600;
    line-height: 1.3;
    margin-top: 1.75em;
    margin-bottom: 0.75em;
  }
  
  .markdown-content h4,
  .markdown-content h5,
  .markdown-content h6 {
    font-size: 1em;
    font-weight: 600;
    line-height: 1.3;
    margin-top: 1.5em;
    margin-bottom: 0.75em;
  }
  
  .markdown-content h1:first-child,
  .markdown-content h2:first-child,
  .markdown-content h3:first-child,
  .markdown-content h4:first-child,
  .markdown-content h5:first-child,
  .markdown-content h6:first-child {
    margin-top: 0;
  }
  
  .markdown-content code {
    font-family: 'SF Mono', 'Monaco', 'Consolas', 'Liberation Mono', 'Courier New', monospace;
    font-size: 0.875em;
  }
  
  .markdown-content :not(pre) > code {
    padding: 0.125em 0.375em;
    background-color: hsl(var(--muted) / 0.8);
    border-radius: 4px;
    border: 1px solid hsl(var(--border) / 0.5);
  }
  
  .markdown-content pre {
    margin: 2em 0;
    overflow-x: auto;
    border-radius: 8px;
    line-height: 1.5;
  }
  
  .markdown-content ul,
  .markdown-content ol {
    padding-left: 1.5em;
    margin: 1.25em 0;
  }
  
  .markdown-content ul {
    list-style-type: disc;
  }
  
  .markdown-content ol {
    list-style-type: decimal;
  }
  
  .markdown-content li {
    margin: 0.5em 0;
    line-height: 1.7;
  }
  
  .markdown-content li > p {
    margin: 0;
  }
  
  .markdown-content li::marker {
    color: hsl(var(--muted-foreground));
  }
  
  .markdown-content li + li {
    margin-top: 0.5em;
  }
  
  .markdown-content ul ul,
  .markdown-content ol ol,
  .markdown-content ul ol,
  .markdown-content ol ul {
    margin: 0.5em 0;
  }
  
  .markdown-content blockquote {
    margin: 2em 0;
    padding-left: 1em;
    border-left: 3px solid hsl(var(--border));
    color: hsl(var(--muted-foreground));
  }
  
  .markdown-content table {
    border-collapse: collapse;
    margin: 2em 0;
    width: 100%;
  }
  
  .markdown-content table th,
  .markdown-content table td {
    padding: 0.5em 0.75em;
    border: 1px solid hsl(var(--border));
  }
  
  .markdown-content table th {
    background-color: hsl(var(--muted));
    font-weight: 600;
  }
  
  .markdown-content p {
    margin: 0;
    line-height: 1.7;
  }
  
  .markdown-content strong {
    font-weight: 600;
  }
  
  .markdown-content li strong:first-child {
    display: inline-block;
    margin-bottom: 0.25em;
  }
  
  .markdown-content a {
    color: hsl(var(--primary));
    text-decoration: underline;
    text-decoration-color: transparent;
    transition: text-decoration-color 0.2s;
  }
  
  .markdown-content a:hover {
    text-decoration-color: hsl(var(--primary));
  }
  
  .markdown-content hr {
    border: none;
    border-top: 1px solid hsl(var(--border));
    margin: 2em 0;
  }
`;

export default function MarkdownRenderer({ content, className = '' }) {
  return (
    <>
      <style>{markdownStyles}</style>
      <div className={`markdown-content py-3 ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          // Minimal clean components that rely on CSS styling
          h1: ({ children }) => <h1>{children}</h1>,
          h2: ({ children }) => <h2>{children}</h2>,
          h3: ({ children }) => <h3>{children}</h3>,
          h4: ({ children }) => <h4>{children}</h4>,
          h5: ({ children }) => <h5>{children}</h5>,
          h6: ({ children }) => <h6>{children}</h6>,
          p: ({ children }) => <p>{children}</p>,
          ul: ({ children }) => <ul>{children}</ul>,
          ol: ({ children }) => <ol>{children}</ol>,
          li: ({ children, className }) => (
            <li className={className}>{children}</li>
          ),
          blockquote: ({ children }) => <blockquote>{children}</blockquote>,
          code: ({ children, className }) => {
            const isInline = !className;
            if (isInline) {
              return <code>{children}</code>;
            }
            return <code className={className}>{children}</code>;
          },
          pre: ({ children }) => (
            <pre className="bg-muted p-4 rounded-lg border border-border">
              {children}
            </pre>
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto">
              <table>{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead>{children}</thead>,
          tbody: ({ children }) => <tbody>{children}</tbody>,
          tr: ({ children }) => <tr>{children}</tr>,
          th: ({ children }) => <th>{children}</th>,
          td: ({ children }) => <td>{children}</td>,
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer">
              {children}
            </a>
          ),
          strong: ({ children }) => <strong>{children}</strong>,
          em: ({ children }) => <em>{children}</em>,
          hr: () => <hr />,
          input: ({ type, checked, ...props }) => {
            if (type === 'checkbox') {
              return (
                <input
                  type="checkbox"
                  checked={checked}
                  readOnly
                  className="mr-2 accent-primary"
                  {...props}
                />
              );
            }
            return <input type={type} {...props} />;
          },
        }}
      >
        {content}
      </ReactMarkdown>
      </div>
    </>
  );
} 