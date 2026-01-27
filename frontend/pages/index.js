import { useEffect, useState } from "react";
import Head from "next/head";
import { api } from "../utils/api";
import BasicChunking from "../components/BasicChunking";
import AdvancedGraph from "../components/AdvancedGraph";
import CodeViewer from "../components/CodeViewer";
import Visualise from "../components/Visualise";
import QueryInterface from "../components/QueryInterface";

export default function Home() {
  const [activeTab, setActiveTab] = useState("basic");
  const [health, setHealth] = useState(null);

  // Shared State
  const [uploadFile, setUploadFile] = useState(null);
  const [regexText, setRegexText] = useState("");
  const [chunkResult, setChunkResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  // Advanced State
  const [prompts, setPrompts] = useState([]);
  const [selectedPrompt, setSelectedPrompt] = useState("");
  const [advancedOutput, setAdvancedOutput] = useState(null); // { mermaid: "", json: {} }
  const [advChunking, setAdvChunking] = useState(false);
  const [availableFiles, setAvailableFiles] = useState(["master"]);
  const [selectedFile, setSelectedFile] = useState("master");
  const [currentDocName, setCurrentDocName] = useState("Defence_Standard_00-056_Part_01.txt");
  const [derivedLoading, setDerivedLoading] = useState(false);
  const [derivedResult, setDerivedResult] = useState(null);
  const [availableDerivedGraphs, setAvailableDerivedGraphs] = useState([]);
  const [selectedDerivedTypes, setSelectedDerivedTypes] = useState([]);
  const [currentGeneratingGraph, setCurrentGeneratingGraph] = useState(null);
  const [graphGenerationStatus, setGraphGenerationStatus] = useState({}); // { graphType: 'pending'|'generating'|'completed'|'failed' }

  const fetchAvailableFiles = async (docName) => {
    try {
      const name = docName || "Defence_Standard_00-056_Part_01.txt";
      const res = await api.get(`/chunk/advanced/files?document_name=${encodeURIComponent(name)}`);
      const files = res.data?.files || ["master"];
      setAvailableFiles(files);
      if (!files.includes(selectedFile)) {
        setSelectedFile("master");
      }
    } catch (err) {
      console.error("Failed to fetch available files:", err);
      setAvailableFiles(["master"]);
    }
  };

  const fetchResults = async (docName, fileName) => {
    try {
      const name = docName || "Defence_Standard_00-056_Part_01.txt";
      const file = fileName || selectedFile || "master";
      const res = await api.get(`/chunk/advanced/results?document_name=${encodeURIComponent(name)}&file_name=${encodeURIComponent(file)}`);
      if (res.data.mermaid || res.data.json) {
        setAdvancedOutput(res.data);
      } else {
        setAdvancedOutput(null);
      }
    } catch (err) {
      console.error("Failed to fetch existing results:", err);
    }
  };

  const handleFileSelect = (fileName) => {
    setSelectedFile(fileName);
    fetchResults(currentDocName, fileName);
  };

  useEffect(() => {
    api.get("/health").then(r => setHealth(r.data));
    api.get("/regex").then(r => setRegexText(r.data?.regex || ""));
    api.get("/prompts").then(r => {
      const list = r.data?.prompts || [];
      setPrompts(list);
      if (list.length > 0) setSelectedPrompt(list[0]);
    });
    api.get("/derived-graphs").then(r => {
      const graphs = r.data?.graphs || [];
      setAvailableDerivedGraphs(graphs);
      // Default to all selected
      setSelectedDerivedTypes(graphs.map(g => g.type));
    });
    fetchAvailableFiles(currentDocName);
    fetchResults(currentDocName, "master"); // Initial fetch
  }, []);

  const handleRunDefaultChunking = async () => {
    setLoading(true);
    setError(null);
    setChunkResult(null);
    try {
      const response = await api.post("/chunk", {});
      setChunkResult(response.data);
    } catch (err) {
      setError(err?.message || "Chunking failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleRunUploadChunking = async () => {
    if (!uploadFile) {
      setError("Please select a .txt file first.");
      return;
    }
    setLoading(true);
    setError(null);
    setChunkResult(null);
    try {
      const formData = new FormData();
      formData.append("file", uploadFile);
      if (regexText?.trim()) {
        formData.append("regex_text", regexText);
      }
      const response = await api.post("/chunk/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      setChunkResult(response.data);
    } catch (err) {
      setError(err?.message || "Upload chunking failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleRunAdvancedChunking = async () => {
    if (!selectedPrompt) {
      setError("Please select a prompt template.");
      return;
    }
    setAdvChunking(true);
    setError(null);
    setAdvancedOutput(null);
    try {
      const formData = new FormData();
      if (uploadFile) {
        formData.append("file", uploadFile);
      }
      formData.append("prompt_filename", selectedPrompt);
      formData.append("document_name", uploadFile ? uploadFile.name : "Defence_Standard_00-056_Part_01.txt");

      const response = await api.post("/chunk/advanced", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      setAdvancedOutput(response.data || null);
      // Refresh file list after generation
      const docName = uploadFile ? uploadFile.name : "Defence_Standard_00-056_Part_01.txt";
      setCurrentDocName(docName);
      setSelectedFile("master");
      await fetchAvailableFiles(docName);
    } catch (err) {
      setError(err?.message || "Advanced chunking failed.");
    } finally {
      setAdvChunking(false);
    }
  };

  const handleGenerateDerived = async () => {
    console.log("handleGenerateDerived called");
    console.log("selectedDerivedTypes:", selectedDerivedTypes);
    console.log("currentDocName:", currentDocName);

    const typesToGenerate = selectedDerivedTypes.length > 0 ? selectedDerivedTypes : availableDerivedGraphs.map(g => g.type);

    setDerivedLoading(true);
    setError(null);
    setDerivedResult(null);

    // Initialize status for all selected graphs
    const initialStatus = {};
    typesToGenerate.forEach(type => {
      initialStatus[type] = 'pending';
    });
    setGraphGenerationStatus(initialStatus);

    const allResults = [];
    const totalTokens = { input_tokens: 0, output_tokens: 0, total_tokens: 0 };
    let provider = null;

    try {
      // Generate each graph sequentially with its own timeout
      for (const graphType of typesToGenerate) {
        const graphInfo = availableDerivedGraphs.find(g => g.type === graphType);
        const graphName = graphInfo?.name || graphType;

        console.log(`Generating ${graphName}...`);
        setCurrentGeneratingGraph(graphName);
        setGraphGenerationStatus(prev => ({ ...prev, [graphType]: 'generating' }));

        try {
          const response = await api.post("/chunk/advanced/generate-derived", {
            document_name: currentDocName,
            selected_types: [graphType] // Single graph at a time
          }, {
            timeout: 300000 // 5 minutes per graph
          });

          console.log(`${graphName} completed:`, response.data);

          if (response.data.success && response.data.graphs.length > 0) {
            const graphResult = response.data.graphs[0];
            allResults.push(graphResult);

            // Accumulate token usage
            totalTokens.input_tokens += graphResult.tokens.input_tokens;
            totalTokens.output_tokens += graphResult.tokens.output_tokens;
            totalTokens.total_tokens += graphResult.tokens.total_tokens;

            // Store provider from first successful response
            if (!provider && response.data.provider) {
              provider = response.data.provider;
            }

            // Mark as completed
            setGraphGenerationStatus(prev => ({ ...prev, [graphType]: 'completed' }));
          } else {
            // Graph generation failed
            allResults.push({
              type: graphType,
              name: graphName,
              success: false,
              error: response.data.error || "Generation failed",
              nodes: 0,
              edges: 0,
              tokens: { input_tokens: 0, output_tokens: 0, total_tokens: 0 }
            });

            // Mark as failed
            setGraphGenerationStatus(prev => ({ ...prev, [graphType]: 'failed' }));
          }
        } catch (graphErr) {
          console.error(`Error generating ${graphName}:`, graphErr);
          // Add failed result but continue with other graphs
          allResults.push({
            type: graphType,
            name: graphName,
            success: false,
            error: graphErr?.response?.data?.detail || graphErr?.message || "Generation failed",
            nodes: 0,
            edges: 0,
            tokens: { input_tokens: 0, output_tokens: 0, total_tokens: 0 }
          });

          // Mark as failed
          setGraphGenerationStatus(prev => ({ ...prev, [graphType]: 'failed' }));
        }
      }

      // Build final result
      const finalResult = {
        success: allResults.some(r => r.success), // Success if at least one succeeded
        provider: provider || "unknown",
        graphs: allResults,
        total_tokens: totalTokens,
        document_name: currentDocName
      };

      console.log("All graphs processed, final result:", finalResult);
      setDerivedResult(finalResult);

      // Refresh file list to show new derived graphs
      await fetchAvailableFiles(currentDocName);

      // Show error if some graphs failed
      const failedGraphs = allResults.filter(r => !r.success);
      if (failedGraphs.length > 0) {
        const failedNames = failedGraphs.map(g => g.name).join(", ");
        setError(`Some graphs failed to generate: ${failedNames}`);
      }

    } catch (err) {
      console.error("Error during generation:", err);
      setError(err?.message || "Failed to generate derived graphs.");
    } finally {
      console.log("Setting derivedLoading to false");
      setDerivedLoading(false);
      setCurrentGeneratingGraph(null);
    }
  };

  return (
    <div className="container">
      <Head>
        <title>Worsley | TrustGraph-Lite</title>
      </Head>

      <header style={{ marginBottom: "3rem" }}>
        <h1>Worsley</h1>
        <p className="subtitle">Process and Document Navigator</p>
        <div style={{ fontSize: "0.75rem", color: "var(--success)", opacity: 0.8 }}>
          System Online: {health ? `${health.app} (Active)` : "Connecting..."}
        </div>
      </header>

      <nav className="tabs">
        <div
          className={`tab ${activeTab === 'basic' ? 'active' : ''}`}
          onClick={() => setActiveTab("basic")}
        >
          Basic Chunking
        </div>
        <div
          className={`tab ${activeTab === 'advanced' ? 'active' : ''}`}
          onClick={() => setActiveTab("advanced")}
        >
          Advanced AI Graph
        </div>
        <div
          className={`tab ${activeTab === 'visualise' ? 'active' : ''}`}
          onClick={() => setActiveTab("visualise")}
        >
          Visualise
        </div>
        <div
          className={`tab ${activeTab === 'query' ? 'active' : ''}`}
          onClick={() => setActiveTab("query")}
        >
          Query Document
        </div>
      </nav>

      <main>
        {activeTab === "basic" && (
          <>
            <BasicChunking
              onRunDefault={handleRunDefaultChunking}
              onRunUpload={handleRunUploadChunking}
              onFileChange={(file) => {
                setUploadFile(file);
                const docName = file ? file.name : "Defence_Standard_00-056_Part_01.txt";
                setCurrentDocName(docName);
                setSelectedFile("master");
                fetchAvailableFiles(docName);
                fetchResults(docName, "master");
              }}
              regexText={regexText}
              setRegexText={setRegexText}
              loading={loading}
              error={error}
              result={chunkResult}
            />
            {chunkResult && (
              <div style={{ marginTop: "2rem" }}>
                <h4 className="label">Chunking Results</h4>
                <CodeViewer
                  code={JSON.stringify(chunkResult, null, 2)}
                  language="json"
                  title="Partitioned Document Schema"
                />
              </div>
            )}
          </>
        )}

        {activeTab === "advanced" && (
          <AdvancedGraph
            prompts={prompts}
            selectedPrompt={selectedPrompt}
            setSelectedPrompt={setSelectedPrompt}
            onGenerate={handleRunAdvancedChunking}
            loading={advChunking}
            error={error}
            outputData={advancedOutput}
            availableFiles={availableFiles}
            selectedFile={selectedFile}
            onFileSelect={handleFileSelect}
            onGenerateDerived={handleGenerateDerived}
            derivedLoading={derivedLoading}
            derivedResult={derivedResult}
            availableDerivedGraphs={availableDerivedGraphs}
            selectedDerivedTypes={selectedDerivedTypes}
            setSelectedDerivedTypes={setSelectedDerivedTypes}
            currentGeneratingGraph={currentGeneratingGraph}
            graphGenerationStatus={graphGenerationStatus}
          />
        )}

        {activeTab === "visualise" && (
          <Visualise
            availableFiles={availableFiles}
            selectedFile={selectedFile}
            onFileSelect={handleFileSelect}
            outputData={advancedOutput}
            documentName={currentDocName}
          />
        )}

        {activeTab === "query" && (
          <QueryInterface
            currentDocName={currentDocName}
            availableIndices={availableFiles.filter(f => f.startsWith('index_'))}
          />
        )}
      </main>

      <footer style={{ marginTop: "4rem", paddingTop: "2rem", borderTop: "1px solid var(--border)", textAlign: "center", color: "var(--text-secondary)", fontSize: "0.875rem" }}>
        &copy; 2026 Barkley Advanced Agentic Coding. All rights reserved.
      </footer>
    </div>
  );
}