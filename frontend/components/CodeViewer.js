import { useState } from "react";

export default function CodeViewer({ code, language = "json", title = "" }) {
    const [copied, setCopied] = useState(false);

    const copyToClipboard = () => {
        navigator.clipboard.writeText(code);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const safeCode = typeof code === 'string' ? code : (code ? JSON.stringify(code, null, 2) : "");
    const lines = safeCode.split("\n");

    return (
        <div className="code-container">
            <div className="code-header">
                <span>{title || language.toUpperCase()}</span>
                <button className="copy-btn" onClick={copyToClipboard}>
                    {copied ? "Copied!" : "Copy"}
                </button>
            </div>
            <div className="code-wrapper">
                <div className="line-numbers">
                    {lines.map((_, i) => (
                        <div key={i}>{i + 1}</div>
                    ))}
                </div>
                <div className="code-block">{safeCode}</div>
            </div>
        </div>
    );
}
