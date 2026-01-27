import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";

export default function D3GraphViewer({ jsonData, documentName }) {
    const svgRef = useRef(null);
    const containerRef = useRef(null);
    const simulationRef = useRef(null);

    const [showLabels, setShowLabels] = useState(false);
    const [nodeFilter, setNodeFilter] = useState("all");
    const [searchTerm, setSearchTerm] = useState("");
    const [stats, setStats] = useState({ total: 0, visible: 0 });
    const [layoutMode, setLayoutMode] = useState("force"); // "force" or "hierarchical"
    const [hierarchicalOrientation, setHierarchicalOrientation] = useState("vertical"); // "vertical" or "horizontal"
    const [nodeSpacing, setNodeSpacing] = useState(80); // Distance between nodes (40-200)

    useEffect(() => {
        if (!jsonData || !jsonData.nodes || !svgRef.current) return;

        // Clear previous
        d3.select(svgRef.current).selectAll("*").remove();
        if (simulationRef.current) {
            simulationRef.current.stop();
        }

        const width = containerRef.current.clientWidth;
        const height = 800;

        // Filter nodes based on filter and search
        const allNodes = jsonData.nodes.map(n => ({
            ...n,
            displayName: `${n.number || ""} ${n.title || n.id}`.trim()
        }));

        let filteredNodes = allNodes;
        if (nodeFilter !== "all") {
            filteredNodes = allNodes.filter(n => n.kind === nodeFilter);
        }
        if (searchTerm) {
            const term = searchTerm.toLowerCase();
            filteredNodes = filteredNodes.filter(n =>
                n.displayName.toLowerCase().includes(term) ||
                n.id.toLowerCase().includes(term)
            );
        }

        const nodeIds = new Set(filteredNodes.map(n => n.id));
        const filteredEdges = (jsonData.edges || [])
            .filter(e => nodeIds.has(e.from) && nodeIds.has(e.to))
            .map(e => ({
                source: e.from,
                target: e.to,
                ...e
            }));

        setStats({ total: allNodes.length, visible: filteredNodes.length });

        // Create SVG
        const svg = d3.select(svgRef.current)
            .attr("width", width)
            .attr("height", height)
            .attr("viewBox", [0, 0, width, height]);

        const g = svg.append("g");

        // Zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 10])
            .on("zoom", (event) => {
                g.attr("transform", event.transform);
                // Auto-show labels when zoomed in
                const shouldShowLabels = event.transform.k > 1.5 || showLabels;
                g.selectAll("text").style("opacity", shouldShowLabels ? 1 : 0);
            });

        svg.call(zoom);

        // Color scale by node kind
        const colorScale = d3.scaleOrdinal()
            .domain(["chapter", "section", "subsection", "clause", "requirement", "reference", "topic", "definition"])
            .range(["#3b82f6", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981", "#ef4444", "#06b6d4", "#6366f1"]);

        let simulation = null;
        let link, node;

        if (layoutMode === "hierarchical") {
            // Create hierarchical tree layout
            // Build tree structure from graph (find root or use first node)
            const nodeMap = new Map(filteredNodes.map(n => [n.id, { ...n, children: [] }]));
            const roots = [];

            // Build parent-child relationships from edges
            filteredEdges.forEach(e => {
                const parent = nodeMap.get(e.source);
                const child = nodeMap.get(e.target);
                if (parent && child) {
                    parent.children.push(child);
                }
            });

            // Find roots (nodes with no incoming edges)
            const childIds = new Set(filteredEdges.map(e => e.target));
            filteredNodes.forEach(n => {
                if (!childIds.has(n.id)) {
                    roots.push(nodeMap.get(n.id));
                }
            });

            // If no clear root, use first node
            if (roots.length === 0 && filteredNodes.length > 0) {
                roots.push(nodeMap.get(filteredNodes[0].id));
            }

            // Create hierarchy and tree layout
            const root = roots.length === 1 ? d3.hierarchy(roots[0]) :
                         d3.hierarchy({ children: roots, id: "root", displayName: "Root" });

            const isVertical = hierarchicalOrientation === "vertical";
            const spacingFactor = nodeSpacing / 80; // Normalize based on default of 80

            // Use nodeSize instead of size for proper spacing control
            const treeLayout = d3.tree()
                .nodeSize(isVertical ?
                    [nodeSpacing * 1.5, nodeSpacing * 2] :
                    [nodeSpacing * 2, nodeSpacing * 1.5])
                .separation((a, b) => (a.parent === b.parent ? 1 : 1.5));

            treeLayout(root);

            // Extract nodes and links from hierarchy
            const hierarchyNodes = root.descendants();
            const hierarchyLinks = root.links();

            // Calculate bounds to center the tree
            let minX = Infinity, maxX = -Infinity;
            let minY = Infinity, maxY = -Infinity;
            hierarchyNodes.forEach(d => {
                if (isVertical) {
                    if (d.x < minX) minX = d.x;
                    if (d.x > maxX) maxX = d.x;
                    if (d.y < minY) minY = d.y;
                    if (d.y > maxY) maxY = d.y;
                } else {
                    if (d.y < minX) minX = d.y;
                    if (d.y > maxX) maxX = d.y;
                    if (d.x < minY) minY = d.x;
                    if (d.x > maxY) maxY = d.x;
                }
            });

            const treeWidth = maxX - minX;
            const treeHeight = maxY - minY;
            const offsetX = (width - treeWidth) / 2 - minX;
            const offsetY = 50 - minY;

            // Draw links
            const linkGenerator = isVertical ?
                d3.linkVertical()
                    .x(d => d.x + offsetX)
                    .y(d => d.y + offsetY) :
                d3.linkHorizontal()
                    .x(d => d.y + offsetX)
                    .y(d => d.x + offsetY);

            link = g.append("g")
                .selectAll("path")
                .data(hierarchyLinks)
                .join("path")
                .attr("d", linkGenerator)
                .attr("fill", "none")
                .attr("stroke", "#475569")
                .attr("stroke-opacity", 0.6)
                .attr("stroke-width", 1);

            // Draw nodes
            node = g.append("g")
                .selectAll("g")
                .data(hierarchyNodes)
                .join("g")
                .attr("transform", d => isVertical ?
                    `translate(${d.x + offsetX},${d.y + offsetY})` :
                    `translate(${d.y + offsetX},${d.x + offsetY})`)
                .attr("cursor", "pointer");

        } else {
            // Force-directed layout
            const spacingFactor = nodeSpacing / 80; // Normalize based on default of 80
            simulation = d3.forceSimulation(filteredNodes)
                .force("link", d3.forceLink(filteredEdges)
                    .id(d => d.id)
                    .distance(nodeSpacing)
                    .strength(0.5)
                )
                .force("charge", d3.forceManyBody()
                    .strength(-300 * spacingFactor)
                    .distanceMax(400 * spacingFactor)
                )
                .force("center", d3.forceCenter(width / 2, height / 2))
                .force("collision", d3.forceCollide().radius(25))
                .force("x", d3.forceX(width / 2).strength(0.05))
                .force("y", d3.forceY(height / 2).strength(0.05));

            simulationRef.current = simulation;

            // Draw links
            link = g.append("g")
                .selectAll("line")
                .data(filteredEdges)
                .join("line")
                .attr("stroke", "#475569")
                .attr("stroke-opacity", 0.6)
                .attr("stroke-width", 1);

            // Draw nodes
            node = g.append("g")
                .selectAll("g")
                .data(filteredNodes)
                .join("g")
                .attr("cursor", "pointer")
                .call(drag(simulation));
        }

        node.append("circle")
            .attr("r", d => {
                const nodeData = d.data || d;
                if (nodeData.kind === "chapter") return 12;
                if (nodeData.kind === "section") return 10;
                if (nodeData.kind === "reference") return 8;
                return 6;
            })
            .attr("fill", d => {
                const nodeData = d.data || d;
                return colorScale(nodeData.kind || "other");
            })
            .attr("stroke", "#1f2937")
            .attr("stroke-width", 2);

        // Add labels (hidden by default)
        node.append("text")
            .text(d => {
                const nodeData = d.data || d;
                return nodeData.displayName;
            })
            .attr("x", 15)
            .attr("y", 4)
            .attr("font-size", "11px")
            .attr("fill", "#e5e7eb")
            .style("opacity", showLabels ? 1 : 0)
            .style("pointer-events", "none");

        // Tooltip
        const tooltip = d3.select("body").append("div")
            .attr("class", "d3-tooltip")
            .style("position", "absolute")
            .style("visibility", "hidden")
            .style("background-color", "rgba(0, 0, 0, 0.9)")
            .style("color", "#fff")
            .style("padding", "8px 12px")
            .style("border-radius", "4px")
            .style("font-size", "12px")
            .style("pointer-events", "none")
            .style("z-index", "1000");

        node.on("mouseover", function(event, d) {
            const nodeData = d.data || d;
            d3.select(this).select("circle")
                .attr("stroke-width", 4)
                .attr("stroke", "#60a5fa");

            tooltip
                .style("visibility", "visible")
                .html(`
                    <strong>${nodeData.displayName}</strong><br/>
                    Type: ${nodeData.kind || "unknown"}<br/>
                    ID: ${nodeData.id}
                    ${nodeData.appears_on_pages ? `<br/>Pages: ${nodeData.appears_on_pages.join(", ")}` : ""}
                `);
        })
        .on("mousemove", function(event) {
            tooltip
                .style("top", (event.pageY - 10) + "px")
                .style("left", (event.pageX + 10) + "px");
        })
        .on("mouseout", function() {
            d3.select(this).select("circle")
                .attr("stroke-width", 2)
                .attr("stroke", "#1f2937");
            tooltip.style("visibility", "hidden");
        });

        // Update positions on simulation tick (force mode only)
        if (simulation) {
            simulation.on("tick", () => {
                link
                    .attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);

                node.attr("transform", d => `translate(${d.x},${d.y})`);
            });
        }

        // Cleanup
        return () => {
            if (simulation) simulation.stop();
            tooltip.remove();
        };

    }, [jsonData, documentName, showLabels, nodeFilter, searchTerm, layoutMode, hierarchicalOrientation, nodeSpacing]);

    function drag(simulation) {
        function dragstarted(event) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        }

        function dragged(event) {
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        }

        function dragended(event) {
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
        }

        return d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended);
    }

    if (!jsonData || !jsonData.nodes || jsonData.nodes.length === 0) {
        return (
            <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-secondary)" }}>
                No graph data available
            </div>
        );
    }

    // Get unique node types for filter
    const nodeTypes = ["all", ...new Set(jsonData.nodes.map(n => n.kind).filter(Boolean))];

    return (
        <div style={{ width: "100%" }}>
            {/* Controls */}
            <div style={{
                display: "flex",
                gap: "1rem",
                marginBottom: "1rem",
                flexWrap: "wrap",
                alignItems: "center",
                fontSize: "0.875rem"
            }}>
                <div>
                    <label style={{ marginRight: "0.5rem", color: "var(--text-secondary)" }}>
                        Layout:
                    </label>
                    <select
                        value={layoutMode}
                        onChange={(e) => setLayoutMode(e.target.value)}
                        className="select"
                        style={{ fontSize: "0.875rem", padding: "0.25rem 0.5rem" }}
                    >
                        <option value="force">Force-Directed</option>
                        <option value="hierarchical">Hierarchical</option>
                    </select>
                </div>

                {layoutMode === "hierarchical" && (
                    <div>
                        <label style={{ marginRight: "0.5rem", color: "var(--text-secondary)" }}>
                            Orientation:
                        </label>
                        <select
                            value={hierarchicalOrientation}
                            onChange={(e) => setHierarchicalOrientation(e.target.value)}
                            className="select"
                            style={{ fontSize: "0.875rem", padding: "0.25rem 0.5rem" }}
                        >
                            <option value="vertical">Top-Down</option>
                            <option value="horizontal">Left-Right</option>
                        </select>
                    </div>
                )}

                <div>
                    <label style={{ marginRight: "0.5rem", color: "var(--text-secondary)" }}>
                        Filter by type:
                    </label>
                    <select
                        value={nodeFilter}
                        onChange={(e) => setNodeFilter(e.target.value)}
                        className="select"
                        style={{ fontSize: "0.875rem", padding: "0.25rem 0.5rem" }}
                    >
                        {nodeTypes.map(type => (
                            <option key={type} value={type}>
                                {type === "all" ? "All Types" : type}
                            </option>
                        ))}
                    </select>
                </div>

                <div>
                    <label style={{ marginRight: "0.5rem", color: "var(--text-secondary)" }}>
                        Search:
                    </label>
                    <input
                        type="text"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        placeholder="Search nodes..."
                        className="input"
                        style={{ fontSize: "0.875rem", padding: "0.25rem 0.5rem", width: "200px" }}
                    />
                </div>

                <div>
                    <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer" }}>
                        <input
                            type="checkbox"
                            checked={showLabels}
                            onChange={(e) => setShowLabels(e.target.checked)}
                        />
                        <span style={{ color: "var(--text-secondary)" }}>Show all labels</span>
                    </label>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <label style={{ color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
                        Node spacing:
                    </label>
                    <input
                        type="range"
                        min="40"
                        max="200"
                        value={nodeSpacing}
                        onChange={(e) => setNodeSpacing(Number(e.target.value))}
                        style={{ width: "120px" }}
                    />
                    <span style={{ color: "var(--text-secondary)", fontSize: "0.75rem", minWidth: "30px" }}>
                        {nodeSpacing}
                    </span>
                </div>

                <div style={{ marginLeft: "auto", color: "var(--text-secondary)" }}>
                    Showing {stats.visible} of {stats.total} nodes
                </div>
            </div>

            {/* Graph Container */}
            <div
                ref={containerRef}
                style={{
                    width: "100%",
                    height: "800px",
                    background: "var(--bg-secondary)",
                    borderRadius: "8px",
                    overflow: "hidden",
                    position: "relative",
                    border: "1px solid var(--border)"
                }}
            >
                <div style={{
                    position: "absolute",
                    top: "1rem",
                    left: "1rem",
                    color: "var(--text-secondary)",
                    fontSize: "0.75rem",
                    background: "rgba(0, 0, 0, 0.7)",
                    padding: "0.5rem 1rem",
                    borderRadius: "4px",
                    zIndex: 10,
                    lineHeight: "1.5"
                }}>
                    <div>💡 <strong>Tips:</strong></div>
                    <div>• Switch between Force-Directed and Hierarchical layouts</div>
                    {layoutMode === "hierarchical" && <div>• Choose Top-Down or Left-Right orientation</div>}
                    <div>• Adjust node spacing slider to spread nodes apart</div>
                    <div>• Hover over nodes for details</div>
                    {layoutMode === "force" && <div>• Drag nodes to reposition</div>}
                    <div>• Scroll to zoom (labels appear when zoomed)</div>
                    <div>• Drag background to pan</div>
                </div>

                {/* Legend */}
                <div style={{
                    position: "absolute",
                    bottom: "1rem",
                    right: "1rem",
                    color: "var(--text-secondary)",
                    fontSize: "0.75rem",
                    background: "rgba(0, 0, 0, 0.7)",
                    padding: "0.5rem 1rem",
                    borderRadius: "4px",
                    zIndex: 10
                }}>
                    <div style={{ fontWeight: 600, marginBottom: "0.25rem" }}>Node Types:</div>
                    <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
                        <div><span style={{ color: "#3b82f6" }}>●</span> Chapter</div>
                        <div><span style={{ color: "#8b5cf6" }}>●</span> Section</div>
                        <div><span style={{ color: "#ef4444" }}>●</span> Reference</div>
                        <div><span style={{ color: "#10b981" }}>●</span> Requirement</div>
                    </div>
                </div>

                <svg ref={svgRef} style={{ width: "100%", height: "100%" }} />
            </div>
        </div>
    );
}
