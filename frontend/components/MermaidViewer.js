import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";

export default function MermaidViewer({ code }) {
    const containerRef = useRef(null);
    const svgRef = useRef(null);
    const [scale, setScale] = useState(1);
    const [position, setPosition] = useState({ x: 0, y: 0 });
    const [isDragging, setIsDragging] = useState(false);
    const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

    useEffect(() => {
        if (!code || !containerRef.current) return;

        // Initialize mermaid with configuration
        mermaid.initialize({
            startOnLoad: false,
            theme: "dark",
            securityLevel: "loose",
            flowchart: {
                useMaxWidth: false,
                htmlLabels: true,
                curve: "basis"
            }
        });

        // Generate unique ID for this diagram
        const id = `mermaid-${Date.now()}`;

        // Render the diagram
        const renderDiagram = async () => {
            try {
                containerRef.current.innerHTML = "";
                const { svg } = await mermaid.render(id, code);
                containerRef.current.innerHTML = svg;

                // Get reference to the SVG element
                svgRef.current = containerRef.current.querySelector('svg');
                if (svgRef.current) {
                    svgRef.current.style.cursor = 'grab';
                }

                // Reset zoom and position when new diagram loads
                setScale(1);
                setPosition({ x: 0, y: 0 });
            } catch (error) {
                console.error("Mermaid rendering error:", error);
                containerRef.current.innerHTML = `<div style="color: var(--error); padding: 1rem;">
                    Error rendering diagram: ${error.message}
                </div>`;
            }
        };

        renderDiagram();
    }, [code]);

    // Apply transform to SVG
    useEffect(() => {
        if (svgRef.current) {
            svgRef.current.style.transform = `translate(${position.x}px, ${position.y}px) scale(${scale})`;
            svgRef.current.style.transformOrigin = 'center center';
            svgRef.current.style.transition = isDragging ? 'none' : 'transform 0.1s ease-out';
        }
    }, [scale, position, isDragging]);

    const handleWheel = (e) => {
        e.preventDefault();
        const delta = e.deltaY > 0 ? 0.9 : 1.1;
        setScale(prevScale => Math.min(Math.max(0.1, prevScale * delta), 5));
    };

    const handleMouseDown = (e) => {
        if (e.button === 0) { // Left click only
            setIsDragging(true);
            setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y });
            if (svgRef.current) {
                svgRef.current.style.cursor = 'grabbing';
            }
        }
    };

    const handleMouseMove = (e) => {
        if (isDragging) {
            setPosition({
                x: e.clientX - dragStart.x,
                y: e.clientY - dragStart.y
            });
        }
    };

    const handleMouseUp = () => {
        setIsDragging(false);
        if (svgRef.current) {
            svgRef.current.style.cursor = 'grab';
        }
    };

    const handleZoomIn = () => {
        setScale(prevScale => Math.min(prevScale * 1.2, 5));
    };

    const handleZoomOut = () => {
        setScale(prevScale => Math.max(prevScale * 0.8, 0.1));
    };

    const handleReset = () => {
        setScale(1);
        setPosition({ x: 0, y: 0 });
    };

    if (!code) {
        return (
            <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-secondary)" }}>
                No diagram available
            </div>
        );
    }

    return (
        <div style={{ position: "relative" }}>
            {/* Zoom Controls */}
            <div style={{
                position: "absolute",
                top: "1rem",
                right: "1rem",
                display: "flex",
                gap: "0.5rem",
                zIndex: 10,
                background: "rgba(0, 0, 0, 0.7)",
                padding: "0.5rem",
                borderRadius: "8px"
            }}>
                <button
                    onClick={handleZoomIn}
                    style={{
                        padding: "0.5rem 1rem",
                        background: "var(--accent)",
                        color: "white",
                        border: "none",
                        borderRadius: "4px",
                        cursor: "pointer",
                        fontSize: "1rem",
                        fontWeight: "bold"
                    }}
                    title="Zoom In"
                >
                    +
                </button>
                <button
                    onClick={handleZoomOut}
                    style={{
                        padding: "0.5rem 1rem",
                        background: "var(--accent)",
                        color: "white",
                        border: "none",
                        borderRadius: "4px",
                        cursor: "pointer",
                        fontSize: "1rem",
                        fontWeight: "bold"
                    }}
                    title="Zoom Out"
                >
                    −
                </button>
                <button
                    onClick={handleReset}
                    style={{
                        padding: "0.5rem 1rem",
                        background: "var(--bg-tertiary)",
                        color: "var(--text-primary)",
                        border: "1px solid var(--border)",
                        borderRadius: "4px",
                        cursor: "pointer",
                        fontSize: "0.875rem"
                    }}
                    title="Reset View"
                >
                    Reset
                </button>
                <div style={{
                    padding: "0.5rem 1rem",
                    color: "var(--text-secondary)",
                    fontSize: "0.875rem",
                    display: "flex",
                    alignItems: "center"
                }}>
                    {Math.round(scale * 100)}%
                </div>
            </div>

            {/* Instructions */}
            <div style={{
                position: "absolute",
                top: "1rem",
                left: "1rem",
                color: "var(--text-secondary)",
                fontSize: "0.875rem",
                background: "rgba(0, 0, 0, 0.7)",
                padding: "0.5rem 1rem",
                borderRadius: "4px",
                zIndex: 10
            }}>
                Scroll to zoom • Drag to pan
            </div>

            {/* Mermaid Container */}
            <div
                onWheel={handleWheel}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
                style={{
                    width: "100%",
                    height: "800px",
                    overflow: "hidden",
                    background: "var(--bg-secondary)",
                    borderRadius: "8px",
                    position: "relative",
                    userSelect: "none"
                }}
            >
                <div
                    ref={containerRef}
                    style={{
                        display: "flex",
                        justifyContent: "center",
                        alignItems: "center",
                        minHeight: "100%",
                        padding: "2rem"
                    }}
                />
            </div>
        </div>
    );
}
