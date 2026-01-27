import { useState } from "react";
import MermaidViewer from "./MermaidViewer";
import D3GraphViewer from "./D3GraphViewer";

export default function Visualise({
    availableFiles,
    selectedFile,
    onFileSelect,
    outputData,
    documentName
}) {
    const [viewMode, setViewMode] = useState("mermaid");

    const mermaidCode = outputData?.mermaid || "";
    const jsonData = outputData?.json || null;

    const formatFileName = (fileName) => {
        if (fileName === "master") return "Master (All Pages)";
        if (fileName === "index_file") return "File Index";
        if (fileName === "index_chapter") return "Chapter Index";
        if (fileName === "index_reference") return "Reference Index";
        if (fileName === "index_section") return "Section Index";
        if (fileName === "index_topic") return "Topic Index";
        const match = fileName.match(/page_(\d+)/);
        return match ? `Page ${match[1]}` : fileName;
    };

    return (
        <div className="card">
            <h3>Knowledge Graph Visualization</h3>
            <p className="subtitle">Interactive visualization of document structure and relationships.</p>

            <div className="form-group">
                <label className="label">Select View</label>
                <select
                    className="select"
                    value={selectedFile}
                    onChange={(e) => onFileSelect(e.target.value)}
                >
                    {availableFiles.map(file => (
                        <option key={file} value={file}>
                            {formatFileName(file)}
                        </option>
                    ))}
                </select>
            </div>

            <div className="tabs" style={{ marginBottom: "1rem" }}>
                <div
                    className={`tab ${viewMode === 'mermaid' ? 'active' : ''}`}
                    onClick={() => setViewMode("mermaid")}
                >
                    Mermaid Diagram
                </div>
                <div
                    className={`tab ${viewMode === 'graph' ? 'active' : ''}`}
                    onClick={() => setViewMode("graph")}
                >
                    Interactive Graph
                </div>
            </div>

            {viewMode === "mermaid" && (
                <MermaidViewer code={mermaidCode} />
            )}

            {viewMode === "graph" && (
                <D3GraphViewer jsonData={jsonData} documentName={documentName} />
            )}
        </div>
    );
}
