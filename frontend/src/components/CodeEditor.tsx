import React from 'react';
import MonacoEditor from '@monaco-editor/react';
import { ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline';
import { toast } from 'react-toastify';

interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  language: string;
  height?: string;
  showControls?: boolean;
  onRun?: () => void;
}

const CodeEditor: React.FC<CodeEditorProps> = ({ 
  value, 
  onChange, 
  language, 
  height = '600px', 
  showControls = true,
  onRun 
}) => {
  const [isMinimized, setIsMinimized] = React.useState(false);
  const editorRef = React.useRef<any>(null);

  React.useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      e.preventDefault();
      toast.error('No vibe coding here, pal!');
    };
    const editorDiv = editorRef.current?.containerDomNode;
    if (editorDiv) {
      editorDiv.addEventListener('paste', handlePaste);
      return () => editorDiv.removeEventListener('paste', handlePaste);
    }
  }, []);

  const handleRun = () => {
    if (onRun) {
      onRun();
    }
  };

  const editorHeight = isMinimized ? '50px' : height;

  return (
    <div className="relative w-full">
      {showControls && (
        <div className="absolute right-4 top-2 flex gap-2">
          <button 
            onClick={() => setIsMinimized(!isMinimized)}
            className="p-1 hover:bg-gray-700 rounded"
          >
            {isMinimized ? (
              <ChevronDownIcon className="w-5 h-5" />
            ) : (
              <ChevronUpIcon className="w-5 h-5" />
            )}
          </button>
          <button 
            onClick={handleRun}
            className="p-1 hover:bg-gray-700 rounded"
          >
            Run
          </button>
        </div>
      )}
      <div className="absolute left-4 top-2 flex gap-2 z-10">
        {/* AI Tools Overlay Button */}
        <button
          onClick={() => toast.info('AI tools coming soon!')}
          className="p-1 bg-blue-700 text-white rounded hover:bg-blue-800"
        >
          AI Tools
        </button>
      </div>
      <div className={`h-[${editorHeight}] w-full transition-all duration-300`} ref={editorRef}>
        <MonacoEditor
          height="100%"
          language={language}
          theme="vs-dark"
          value={value}
          onChange={(value) => onChange(value || '')}
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            lineNumbers: 'on',
            roundedSelection: false,
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: 4,
            wordWrap: 'on',
            formatOnPaste: true,
            formatOnType: true,
            quickSuggestions: {
              other: true,
              comments: true,
              strings: true
            }
          }}
        />
      </div>
    </div>
  );
};

export default CodeEditor;
