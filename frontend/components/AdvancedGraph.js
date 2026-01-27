import { useState } from "react";
import CodeViewer from "./CodeViewer";

export default function AdvancedGraph({
    prompts,
    selectedPrompt,
    setSelectedPrompt,
    onGenerate,
    loading,
    error,
    outputData,
    availableFiles,
    selectedFile,
    onFileSelect,
    onGenerateDerived,
    derivedLoading,
    derivedResult,
    availableDerivedGraphs,
    selectedDerivedTypes,
    setSelectedDerivedTypes,
    currentGeneratingGraph,
    graphGenerationStatus
}) {
    const [viewMode, setViewMode] = useState("mermaid");

    const mermaidOutput = outputData?.mermaid || "";
    const jsonOutput = outputData?.json ? JSON.stringify(outputData.json, null, 2) : "";

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

    const handleToggleDerivedGraph = (type) => {
        console.log("Toggling graph type:", type);
        console.log("Current selectedDerivedTypes:", selectedDerivedTypes);

        if (selectedDerivedTypes.includes(type)) {
            const newTypes = selectedDerivedTypes.filter(t => t !== type);
            console.log("Removing, new types:", newTypes);
            setSelectedDerivedTypes(newTypes);
        } else {
            const newTypes = [...selectedDerivedTypes, type];
            console.log("Adding, new types:", newTypes);
            setSelectedDerivedTypes(newTypes);
        }
    };

    const handleSelectAllDerived = () => {
        if (selectedDerivedTypes.length === availableDerivedGraphs.length) {
            setSelectedDerivedTypes([]);
        } else {
            setSelectedDerivedTypes(availableDerivedGraphs.map(g => g.type));
        }
    };

    return (
        <div style={{
            display: "grid",
            gridTemplateColumns: "minmax(0, 2fr) minmax(0, 1fr)",
            gap: "2rem",
            width: "100%",
            maxWidth: "100%"
        }}>
            {/* Left Column: Generation Controls */}
            <div style={{ minWidth: 0, overflow: "hidden" }}>
                <div className="card">
                    <h3>Semantic Graph Generation</h3>
                    <p className="subtitle">Construct a deterministic, relationship-aware index using specialized AI prompts.</p>

                    {/* Section 1: Master Graph Generation */}
                    <div style={{ marginBottom: "2rem", paddingBottom: "1.5rem", borderBottom: "1px solid var(--border)" }}>
                        <h4 style={{ fontSize: "1.1rem", marginBottom: "1rem", color: "var(--text-primary)" }}>
                            1. Master Graph Generation
                        </h4>
                        <p style={{ fontSize: "0.9rem", color: "var(--text-secondary)", marginBottom: "1rem" }}>
                            Process the raw document to extract semantic relationships and create the master graph.
                        </p>

                        <div className="form-group">
                            <label className="label">Processing Strategy</label>
                            <select
                                className="select"
                                value={selectedPrompt}
                                onChange={(e) => setSelectedPrompt(e.target.value)}
                            >
                                {prompts.map(p => <option key={p} value={p}>{p}</option>)}
                            </select>
                        </div>

                        <div className="form-group">
                            <button
                                className="btn btn-primary"
                                onClick={onGenerate}
                                disabled={loading || derivedLoading}
                            >
                                {loading ? "Synthesizing Knowledge Graph..." : "Generate Master Graph"}
                            </button>
                        </div>
                    </div>

                    {/* Section 2: Derived Graph Generation */}
                    <div style={{ marginBottom: "1rem" }}>
                        <h4 style={{ fontSize: "1.1rem", marginBottom: "1rem", color: "var(--text-primary)" }}>
                            2. Derived Graph Generation
                        </h4>
                        <p style={{ fontSize: "0.9rem", color: "var(--text-secondary)", marginBottom: "1rem" }}>
                            Transform the master graph into specialized views optimized for different use cases.
                        </p>

                        {!outputData && (
                            <div style={{
                                padding: "1rem",
                                backgroundColor: "var(--bg-tertiary)",
                                borderRadius: "0.5rem",
                                fontSize: "0.9rem",
                                color: "var(--text-secondary)",
                                marginBottom: "1rem"
                            }}>
                                Generate the master graph first before creating derived graphs.
                            </div>
                        )}

                        {outputData && availableDerivedGraphs.length > 0 && (
                            <>
                                <div style={{ marginBottom: "1rem" }}>
                                    <div style={{
                                        display: "flex",
                                        justifyContent: "space-between",
                                        alignItems: "center",
                                        marginBottom: "0.5rem"
                                    }}>
                                        <label className="label" style={{ marginBottom: 0 }}>Select Graphs to Generate</label>
                                        <button
                                            onClick={handleSelectAllDerived}
                                            style={{
                                                background: "none",
                                                border: "none",
                                                color: "var(--accent)",
                                                cursor: "pointer",
                                                fontSize: "0.875rem",
                                                textDecoration: "underline"
                                            }}
                                        >
                                            {selectedDerivedTypes.length === availableDerivedGraphs.length ? "Deselect All" : "Select All"}
                                        </button>
                                    </div>

                                    <table style={{
                                        width: "100%",
                                        borderCollapse: "collapse",
                                        fontSize: "0.875rem",
                                        tableLayout: "fixed"
                                    }}>
                                        <thead>
                                            <tr style={{ borderBottom: "1px solid var(--border)" }}>
                                                <th style={{ padding: "0.5rem", textAlign: "left", width: "40px" }}></th>
                                                <th style={{ padding: "0.5rem", textAlign: "left", width: "30%" }}>Graph Type</th>
                                                <th style={{ padding: "0.5rem", textAlign: "left" }}>Description</th>
                                                <th style={{ padding: "0.5rem", textAlign: "center", width: "80px" }}>Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {availableDerivedGraphs.map((graph) => (
                                                <tr
                                                    key={graph.type}
                                                    style={{
                                                        borderBottom: "1px solid var(--border)",
                                                        cursor: "pointer",
                                                        backgroundColor: selectedDerivedTypes.includes(graph.type) ? "rgba(59, 130, 246, 0.1)" : "transparent"
                                                    }}
                                                    onClick={() => handleToggleDerivedGraph(graph.type)}
                                                >
                                                    <td style={{ padding: "0.75rem" }}>
                                                        <input
                                                            type="checkbox"
                                                            checked={selectedDerivedTypes.includes(graph.type)}
                                                            onChange={() => handleToggleDerivedGraph(graph.type)}
                                                            onClick={(e) => e.stopPropagation()}
                                                            style={{ cursor: "pointer" }}
                                                        />
                                                    </td>
                                                    <td style={{ padding: "0.75rem", fontWeight: 500, wordWrap: "break-word" }}>
                                                        {graph.name}
                                                    </td>
                                                    <td style={{ padding: "0.75rem", color: "var(--text-secondary)", wordWrap: "break-word" }}>
                                                        {graph.description}
                                                    </td>
                                                    <td style={{ padding: "0.75rem", textAlign: "center" }}>
                                                        {graphGenerationStatus[graph.type] === 'generating' && (
                                                            <span style={{ color: "var(--accent)" }}>⏳</span>
                                                        )}
                                                        {graphGenerationStatus[graph.type] === 'completed' && (
                                                            <span style={{ color: "var(--success)", fontSize: "1.2rem" }}>✓</span>
                                                        )}
                                                        {graphGenerationStatus[graph.type] === 'failed' && (
                                                            <span style={{ color: "var(--error)", fontSize: "1.2rem" }}>✗</span>
                                                        )}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>

                                <div className="form-group">
                                    <button
                                        className="btn btn-secondary"
                                        onClick={() => {
                                            console.log("Generate button clicked!");
                                            console.log("Button state - loading:", loading, "derivedLoading:", derivedLoading, "selectedCount:", selectedDerivedTypes.length);
                                            onGenerateDerived();
                                        }}
                                        disabled={loading || derivedLoading || selectedDerivedTypes.length === 0}
                                        title={selectedDerivedTypes.length === 0 ? "Select at least one graph type" : "Generate selected derived graphs"}
                                    >
                                        {derivedLoading
                                            ? (currentGeneratingGraph ? `Generating ${currentGeneratingGraph}...` : "Generating Derived Graphs...")
                                            : `Generate ${selectedDerivedTypes.length} Selected Graph${selectedDerivedTypes.length !== 1 ? 's' : ''}`}
                                    </button>
                                    {console.log("Render - Button disabled?", loading || derivedLoading || selectedDerivedTypes.length === 0, "loading:", loading, "derivedLoading:", derivedLoading, "selectedCount:", selectedDerivedTypes.length)}
                                </div>
                            </>
                        )}
                    </div>

                    {error && <div className="error-msg">{error}</div>}
                </div>

                {/* File Viewer Section */}
                {(mermaidOutput || jsonOutput) && (
                    <div className="card" style={{ marginTop: "2rem" }}>
                        <div className="form-group">
                            <label className="label">View File</label>
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
                                Mermaid Syntax
                            </div>
                            <div
                                className={`tab ${viewMode === 'json' ? 'active' : ''}`}
                                onClick={() => setViewMode("json")}
                            >
                                Raw Schema (JSON)
                            </div>
                        </div>

                        <CodeViewer
                            code={viewMode === 'mermaid' ? mermaidOutput : jsonOutput}
                            language={viewMode}
                            title={viewMode === 'mermaid' ? "Graph (Mermaid)" : "Structured Relationships (JSON)"}
                        />
                    </div>
                )}
            </div>

            {/* Right Column: Token Usage Display */}
            <div style={{ minWidth: 0, overflow: "hidden" }}>
                {derivedResult && derivedResult.success && (
                    <div className="card" style={{ position: "sticky", top: "2rem", overflow: "auto" }}>
                        <h4 style={{ marginTop: 0, marginBottom: "1rem", color: "var(--success)" }}>
                            ✓ Graphs Generated
                        </h4>

                        <div style={{ fontSize: "0.875rem", marginBottom: "1.5rem" }}>
                            <div style={{ color: "var(--text-secondary)", marginBottom: "0.25rem" }}>Provider</div>
                            <div style={{ fontWeight: 600 }}>{derivedResult.provider}</div>
                        </div>

                        <div style={{ marginBottom: "1.5rem" }}>
                            <h5 style={{ fontSize: "0.95rem", marginBottom: "0.75rem", color: "var(--text-primary)" }}>
                                Generated Graphs
                            </h5>
                            {derivedResult.graphs.map((graph, idx) => (
                                <div
                                    key={idx}
                                    style={{
                                        fontSize: "0.8rem",
                                        padding: "0.75rem",
                                        marginBottom: "0.5rem",
                                        backgroundColor: graph.success ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)",
                                        borderRadius: "0.375rem",
                                        border: `1px solid ${graph.success ? "rgba(16, 185, 129, 0.3)" : "rgba(239, 68, 68, 0.3)"}`
                                    }}
                                >
                                    <div style={{ fontWeight: 600, marginBottom: "0.25rem" }}>
                                        {graph.name}
                                    </div>
                                    <div style={{ color: "var(--text-secondary)", marginBottom: "0.25rem" }}>
                                        {graph.nodes} nodes, {graph.edges} edges
                                    </div>
                                    <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                                        {graph.tokens.input_tokens.toLocaleString()} in + {graph.tokens.output_tokens.toLocaleString()} out = {graph.tokens.total_tokens.toLocaleString()} tokens
                                    </div>
                                </div>
                            ))}
                        </div>

                        <div style={{
                            padding: "1rem",
                            backgroundColor: "rgba(16, 185, 129, 0.1)",
                            borderRadius: "0.375rem",
                            border: "1px solid rgba(16, 185, 129, 0.3)"
                        }}>
                            <div style={{ fontWeight: 600, marginBottom: "0.5rem", fontSize: "0.95rem" }}>
                                Total Token Usage
                            </div>
                            <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                                <div>Input: {derivedResult.total_tokens.input_tokens.toLocaleString()}</div>
                                <div>Output: {derivedResult.total_tokens.output_tokens.toLocaleString()}</div>
                                <div style={{ fontWeight: 600, color: "var(--text-primary)", marginTop: "0.5rem" }}>
                                    Total: {derivedResult.total_tokens.total_tokens.toLocaleString()}
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
