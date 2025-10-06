import React from 'react';
import { Highlight, themes, Language } from 'prism-react-renderer';

interface PrismCodeHighlighterProps {
  code: string;
  language: string;
  className?: string;
}

const PrismCodeHighlighter: React.FC<PrismCodeHighlighterProps> = ({
  code,
  language,
  className = '',
}) => {
  // Map language prop to prism-react-renderer supported languages
  const getLanguage = (lang: string): Language => {
    const languageMap: Record<string, Language> = {
      'python': 'python',
      'javascript': 'javascript',
      'java': 'java',
      'typescript': 'typescript',
      'jsx': 'jsx',
      'tsx': 'tsx',
      'css': 'css',
      'html': 'html',
      'go': 'go',
      'rust': 'rust',
      'c': 'c',
      'cpp': 'cpp',
      'csharp': 'csharp',
      'ruby': 'ruby',
      'php': 'php',
      'sql': 'sql',
      'shell': 'bash',
      'bash': 'bash',
    };

    return languageMap[lang.toLowerCase()] || 'javascript';
  };

  return (
    <Highlight
      theme={themes.nightOwl}
      code={code}
      language={getLanguage(language)}
    >
      {({ className: highlightClassName, style, tokens, getLineProps, getTokenProps }) => (
        <pre 
          className={`${highlightClassName} ${className} overflow-auto p-4 rounded-lg text-sm bg-gray-900`} 
          style={style}
        >
          {tokens.map((line, i) => {
            const { key: lineKey, ...lineProps } = getLineProps({ line, key: i });
            return (
              <div key={i} {...lineProps}>
                <span className="text-gray-500 select-none mr-4">{i + 1}</span>
                {line.map((token, tokenIndex) => {
                  const { key: tokenKey, ...tokenProps } = getTokenProps({ token, key: tokenIndex });
                  return (
                    <span key={tokenIndex} {...tokenProps} />
                  );
                })}
              </div>
            );
          })}
        </pre>
      )}
    </Highlight>
  );
};

export default PrismCodeHighlighter;
