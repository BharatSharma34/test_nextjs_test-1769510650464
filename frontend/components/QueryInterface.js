import { useState } from "react";
import { api } from "../utils/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function QueryInterface({
    currentDocName,
    availableIndices
}) {
    const [query, setQuery] = useState("");
    const [chatHistory, setChatHistory] = useState([]);
    const [loading, setLoading] = useState(false);
    const [classificationResult, setClassificationResult] = useState(null);
    const [showClearConfirm, setShowClearConfirm] = useState(false);

    const handleClearChat = (e) => {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }

        if (chatHistory.length === 0) return;
        setShowClearConfirm(true);
    };

    const confirmClear = () => {
        setChatHistory([]);
        setClassificationResult(null);
        setShowClearConfirm(false);
    };

    const cancelClear = () => {
        setShowClearConfirm(false);
    };

    const handleSubmitQuery = async () => {
        if (!query.trim()) return;

        setLoading(true);

        // Add user message to chat
        const userMessage = {
            role: "user",
            content: query,
            timestamp: new Date().toISOString()
        };
        setChatHistory(prev => [...prev, userMessage]);

        try {
            // Step 1: Classification call
            const classifyResponse = await api.post("/query/classify", {
                user_query: query,
                document_name: currentDocName,
                chat_history: chatHistory,
                available_indices: availableIndices
            });

            const classification = classifyResponse.data.classification || classifyResponse.data.fallback_classification;
            setClassificationResult(classifyResponse.data);

            // Step 2: Execute workflow based on classification
            let result;
            if (classification.workflow === "norag") {
                const response = await api.post("/query/norag", {
                    normalized_query: classification.normalized_query,
                    document_name: currentDocName,
                    suggested_indices: classification.suggested_indices,
                    chat_history: chatHistory
                });
                result = response.data;
            } else {
                const response = await api.post("/query/rag", {
                    normalized_query: classification.normalized_query,
                    document_name: currentDocName,
                    suggested_indices: classification.suggested_indices,
                    chat_history: chatHistory
                });
                result = response.data;
            }

            // Add assistant response to chat
            const assistantMessage = {
                role: "assistant",
                content: result.answer,
                metadata: result.metadata,
                timestamp: new Date().toISOString()
            };
            setChatHistory(prev => [...prev, assistantMessage]);

        } catch (err) {
            console.error("Query error:", err);
            const errorMessage = {
                role: "assistant",
                content: "Sorry, I encountered an error processing your query.",
                error: err.message,
                timestamp: new Date().toISOString()
            };
            setChatHistory(prev => [...prev, errorMessage]);
        } finally {
            setLoading(false);
            setQuery("");
        }
    };

    return (
        <>
            {/* Clear Confirmation Modal */}
            {showClearConfirm && (
                <div style={{
                    position: "fixed",
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    backgroundColor: "rgba(0, 0, 0, 0.5)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    zIndex: 9999
                }}>
                    <div style={{
                        backgroundColor: "var(--bg-primary)",
                        padding: "2rem",
                        borderRadius: "0.5rem",
                        border: "1px solid var(--border)",
                        maxWidth: "400px",
                        width: "90%"
                    }}>
                        <h3 style={{ marginTop: 0, marginBottom: "1rem" }}>Clear Chat History?</h3>
                        <p style={{ marginBottom: "1.5rem", color: "var(--text-secondary)" }}>
                            This will permanently delete all messages in this conversation.
                        </p>
                        <div style={{ display: "flex", gap: "1rem", justifyContent: "flex-end" }}>
                            <button
                                onClick={cancelClear}
                                style={{
                                    padding: "0.5rem 1rem",
                                    backgroundColor: "transparent",
                                    border: "1px solid var(--border)",
                                    borderRadius: "0.375rem",
                                    cursor: "pointer",
                                    color: "var(--text-primary)"
                                }}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={confirmClear}
                                style={{
                                    padding: "0.5rem 1rem",
                                    backgroundColor: "var(--error)",
                                    border: "1px solid var(--error)",
                                    borderRadius: "0.375rem",
                                    cursor: "pointer",
                                    color: "white"
                                }}
                            >
                                Clear Chat
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <div style={{
                display: "grid",
                gridTemplateColumns: "1fr",
                gap: "1.5rem",
                height: "calc(100vh - 200px)"
            }}>
                {/* Chat History */}
            <div className="card" style={{
                display: "flex",
                flexDirection: "column",
                overflow: "hidden"
            }}>
                <div style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "1rem"
                }}>
                    <h3 style={{ margin: 0 }}>
                        Query Document: {currentDocName}
                    </h3>
                    <button
                        type="button"
                        onClick={handleClearChat}
                        disabled={chatHistory.length === 0}
                        style={{
                            padding: "0.5rem 1rem",
                            fontSize: "0.875rem",
                            backgroundColor: chatHistory.length === 0 ? "var(--bg-tertiary)" : "transparent",
                            border: "1px solid var(--border)",
                            borderRadius: "0.375rem",
                            color: chatHistory.length === 0 ? "var(--text-secondary)" : "var(--error)",
                            cursor: chatHistory.length === 0 ? "not-allowed" : "pointer",
                            opacity: chatHistory.length === 0 ? 0.5 : 1
                        }}
                        onMouseOver={(e) => {
                            if (chatHistory.length > 0) {
                                e.target.style.backgroundColor = "rgba(239, 68, 68, 0.1)";
                                e.target.style.borderColor = "var(--error)";
                            }
                        }}
                        onMouseOut={(e) => {
                            e.target.style.backgroundColor = "transparent";
                            e.target.style.borderColor = "var(--border)";
                        }}
                    >
                        Clear Chat
                    </button>
                </div>

                {/* Messages Area */}
                <div style={{
                    flex: 1,
                    overflowY: "auto",
                    marginBottom: "1rem",
                    padding: "1rem",
                    backgroundColor: "var(--bg-secondary)",
                    borderRadius: "0.5rem"
                }}>
                    {chatHistory.length === 0 ? (
                        <div style={{
                            textAlign: "center",
                            color: "var(--text-secondary)",
                            padding: "2rem"
                        }}>
                            <p>No messages yet. Ask a question about the document.</p>
                            <p style={{ fontSize: "0.875rem", marginTop: "0.5rem" }}>
                                The system will analyze your query and determine the best retrieval strategy.
                            </p>
                        </div>
                    ) : (
                        chatHistory.map((msg, idx) => (
                            <div key={idx} style={{
                                marginBottom: "1rem",
                                padding: "0.75rem",
                                backgroundColor: msg.role === "user" ? "rgba(59, 130, 246, 0.1)" : "var(--bg-tertiary)",
                                borderRadius: "0.5rem",
                                borderLeft: msg.role === "user" ? "3px solid var(--accent)" : "3px solid var(--success)"
                            }}>
                                <div style={{
                                    fontSize: "0.75rem",
                                    color: "var(--text-secondary)",
                                    marginBottom: "0.5rem",
                                    fontWeight: 600
                                }}>
                                    {msg.role === "user" ? "You" : "Assistant"}
                                    <span style={{ marginLeft: "0.5rem", fontWeight: 400 }}>
                                        {new Date(msg.timestamp).toLocaleTimeString()}
                                    </span>
                                </div>
                                <div style={{ whiteSpace: "pre-wrap" }}>
                                    {msg.role === "assistant" ? (
                                        <ReactMarkdown
                                            remarkPlugins={[remarkGfm]}
                                            components={{
                                                // Style markdown elements
                                                h1: ({node, ...props}) => <h1 style={{fontSize: "1.5rem", marginTop: "1rem", marginBottom: "0.5rem"}} {...props} />,
                                                h2: ({node, ...props}) => <h2 style={{fontSize: "1.25rem", marginTop: "0.75rem", marginBottom: "0.5rem"}} {...props} />,
                                                h3: ({node, ...props}) => <h3 style={{fontSize: "1.1rem", marginTop: "0.5rem", marginBottom: "0.5rem"}} {...props} />,
                                                p: ({node, ...props}) => <p style={{marginTop: "0.5rem", marginBottom: "0.5rem", lineHeight: "1.6"}} {...props} />,
                                                ul: ({node, ...props}) => <ul style={{marginLeft: "1.5rem", marginTop: "0.5rem", marginBottom: "0.5rem"}} {...props} />,
                                                ol: ({node, ...props}) => <ol style={{marginLeft: "1.5rem", marginTop: "0.5rem", marginBottom: "0.5rem"}} {...props} />,
                                                li: ({node, ...props}) => <li style={{marginTop: "0.25rem"}} {...props} />,
                                                code: ({node, inline, ...props}) => inline
                                                    ? <code style={{backgroundColor: "var(--bg-tertiary)", padding: "0.125rem 0.25rem", borderRadius: "0.25rem", fontSize: "0.9em"}} {...props} />
                                                    : <code style={{display: "block", backgroundColor: "var(--bg-tertiary)", padding: "0.75rem", borderRadius: "0.375rem", overflowX: "auto", fontSize: "0.9em"}} {...props} />,
                                                blockquote: ({node, ...props}) => <blockquote style={{borderLeft: "3px solid var(--accent)", paddingLeft: "1rem", marginLeft: "0", fontStyle: "italic", color: "var(--text-secondary)"}} {...props} />,
                                                strong: ({node, ...props}) => <strong style={{fontWeight: 600}} {...props} />,
                                            }}
                                        >
                                            {msg.content}
                                        </ReactMarkdown>
                                    ) : (
                                        msg.content
                                    )}
                                </div>
                                {msg.metadata && (
                                    <div style={{
                                        marginTop: "0.5rem",
                                        fontSize: "0.75rem",
                                        color: "var(--text-secondary)",
                                        borderTop: "1px solid var(--border)",
                                        paddingTop: "0.5rem"
                                    }}>
                                        <div>
                                            <strong>Workflow:</strong> {msg.metadata.workflow}
                                            {msg.metadata.iterations && ` (${msg.metadata.iterations} iteration${msg.metadata.iterations > 1 ? 's' : ''})`}
                                        </div>
                                        {msg.metadata.indices_used && (
                                            <div>
                                                <strong>Indices:</strong> {msg.metadata.indices_used.join(", ")}
                                            </div>
                                        )}
                                        {msg.metadata.iteration_history && msg.metadata.iteration_history.length > 1 && (
                                            <details style={{ marginTop: "0.5rem" }}>
                                                <summary style={{ cursor: "pointer", color: "var(--accent)" }}>
                                                    View adaptive loading history
                                                </summary>
                                                <div style={{ marginTop: "0.5rem", paddingLeft: "0.5rem" }}>
                                                    {msg.metadata.iteration_history.map((iter, idx) => (
                                                        <div key={idx} style={{ marginBottom: "0.5rem" }}>
                                                            <strong>Iteration {iter.iteration}:</strong> {iter.loaded_indices.join(", ")}
                                                            {iter.is_request && (
                                                                <div style={{ marginLeft: "0.5rem", fontSize: "0.7rem", fontStyle: "italic" }}>
                                                                    → Requested: {iter.requested_indices.join(", ")}
                                                                </div>
                                                            )}
                                                        </div>
                                                    ))}
                                                </div>
                                            </details>
                                        )}
                                        {msg.metadata.retrieval_plan && (
                                            <details style={{ marginTop: "0.5rem" }}>
                                                <summary style={{ cursor: "pointer", color: "var(--accent)", fontWeight: 600 }}>
                                                    📋 View Detailed Retrieval Plan (JSON)
                                                </summary>
                                                <div style={{
                                                    marginTop: "0.75rem",
                                                    padding: "1rem",
                                                    backgroundColor: "var(--bg-secondary)",
                                                    borderRadius: "0.375rem",
                                                    border: "1px solid var(--border)"
                                                }}>
                                                    <div style={{ marginBottom: "1rem" }}>
                                                        <div style={{ fontSize: "0.8rem", marginBottom: "0.5rem" }}>
                                                            <strong>Strategy:</strong> <span style={{ color: "var(--accent)" }}>{msg.metadata.retrieval_plan.strategy}</span>
                                                        </div>
                                                        <div style={{ fontSize: "0.8rem", marginBottom: "0.5rem" }}>
                                                            <strong>Estimated Tokens:</strong> {msg.metadata.retrieval_plan.estimated_tokens?.toLocaleString()}
                                                        </div>
                                                        <div style={{ fontSize: "0.8rem", marginBottom: "0.5rem" }}>
                                                            <strong>Confidence:</strong> {((msg.metadata.retrieval_plan.confidence || 0) * 100).toFixed(0)}%
                                                        </div>
                                                    </div>

                                                    <div style={{ marginBottom: "1rem" }}>
                                                        <strong style={{ fontSize: "0.85rem" }}>Retrieval Steps:</strong>
                                                        {msg.metadata.retrieval_plan.steps?.map((step, idx) => (
                                                            <div key={idx} style={{
                                                                marginTop: "0.75rem",
                                                                padding: "0.75rem",
                                                                backgroundColor: "var(--bg-tertiary)",
                                                                borderRadius: "0.25rem",
                                                                borderLeft: "3px solid var(--accent)"
                                                            }}>
                                                                <div style={{ fontSize: "0.75rem", marginBottom: "0.5rem", fontWeight: 600 }}>
                                                                    Step {idx + 1} ({step.retrieval_method})
                                                                </div>
                                                                <div style={{ fontSize: "0.7rem", marginBottom: "0.5rem", fontStyle: "italic" }}>
                                                                    {step.step_description}
                                                                </div>
                                                                {step.section && (
                                                                    <div style={{ fontSize: "0.7rem", marginTop: "0.25rem" }}>
                                                                        📍 Sections: {step.section.section_numbers.join(", ")}
                                                                    </div>
                                                                )}
                                                                {step.page_range && (
                                                                    <div style={{ fontSize: "0.7rem", marginTop: "0.25rem" }}>
                                                                        📄 Pages: {step.page_range.start_page}-{step.page_range.end_page}
                                                                    </div>
                                                                )}
                                                                {step.keyword_search && (
                                                                    <div style={{ fontSize: "0.7rem", marginTop: "0.25rem" }}>
                                                                        🔍 Keywords: {step.keyword_search.keywords.join(", ")} (proximity: {step.keyword_search.proximity} words)
                                                                    </div>
                                                                )}
                                                                {step.concept_search && (
                                                                    <div style={{ fontSize: "0.7rem", marginTop: "0.25rem" }}>
                                                                        💡 Concept: {step.concept_search.concept}
                                                                    </div>
                                                                )}
                                                            </div>
                                                        ))}
                                                    </div>

                                                    <details>
                                                        <summary style={{ cursor: "pointer", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                                                            View Full JSON
                                                        </summary>
                                                        <pre style={{
                                                            marginTop: "0.5rem",
                                                            padding: "0.5rem",
                                                            backgroundColor: "var(--bg-primary)",
                                                            borderRadius: "0.25rem",
                                                            fontSize: "0.65rem",
                                                            overflow: "auto",
                                                            maxHeight: "300px"
                                                        }}>
                                                            {JSON.stringify(msg.metadata.retrieval_plan, null, 2)}
                                                        </pre>
                                                    </details>
                                                </div>
                                            </details>
                                        )}
                                    </div>
                                )}
                            </div>
                        ))
                    )}
                    {loading && (
                        <div style={{
                            padding: "0.75rem",
                            backgroundColor: "var(--bg-tertiary)",
                            borderRadius: "0.5rem",
                            borderLeft: "3px solid var(--success)"
                        }}>
                            <div style={{
                                fontSize: "0.75rem",
                                color: "var(--text-secondary)",
                                marginBottom: "0.5rem",
                                fontWeight: 600
                            }}>
                                Assistant
                            </div>
                            <div style={{ color: "var(--accent)" }}>
                                Processing your query...
                            </div>
                        </div>
                    )}
                </div>

                {/* Input Area */}
                <div style={{
                    display: "flex",
                    gap: "0.5rem",
                    alignItems: "flex-end"
                }}>
                    <textarea
                        className="textarea"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === "Enter" && !e.shiftKey) {
                                e.preventDefault();
                                handleSubmitQuery();
                            }
                        }}
                        placeholder="Ask a question about the document... (Press Enter to send, Shift+Enter for new line)"
                        disabled={loading}
                        rows={3}
                        style={{
                            flex: 1,
                            resize: "vertical",
                            minHeight: "60px"
                        }}
                    />
                    <button
                        className="btn btn-primary"
                        onClick={handleSubmitQuery}
                        disabled={loading || !query.trim()}
                        style={{ height: "fit-content" }}
                    >
                        {loading ? "Processing..." : "Send"}
                    </button>
                </div>

                {/* Debug: Classification Result */}
                {classificationResult && (
                    <details style={{
                        marginTop: "1rem",
                        fontSize: "0.75rem",
                        color: "var(--text-secondary)"
                    }}>
                        <summary style={{ cursor: "pointer", fontWeight: 600 }}>
                            Classification Debug
                        </summary>
                        <pre style={{
                            marginTop: "0.5rem",
                            padding: "0.5rem",
                            backgroundColor: "var(--bg-secondary)",
                            borderRadius: "0.25rem",
                            overflow: "auto"
                        }}>
                            {JSON.stringify(classificationResult, null, 2)}
                        </pre>
                    </details>
                )}
            </div>
        </div>
        </>
    );
}
