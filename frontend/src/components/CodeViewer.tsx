import { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

interface Props {
  code: string;
}

export default function CodeViewer({ code }: Props) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="code-viewer">
      <button className="copy-btn" onClick={handleCopy}>
        {copied ? "✓ Copied" : "📋 Copy"}
      </button>
      <SyntaxHighlighter language="python" style={oneDark} wrapLongLines>
        {code}
      </SyntaxHighlighter>
    </div>
  );
}
