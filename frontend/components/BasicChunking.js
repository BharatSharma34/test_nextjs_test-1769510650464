export default function BasicChunking({
    onRunDefault,
    onRunUpload,
    onFileChange,
    regexText,
    setRegexText,
    loading,
    error,
    result
}) {
    return (
        <div className="card">
            <h3>Document Partitioning</h3>
            <p className="subtitle">Slice documents into manageable page segments using logical delimiters.</p>

            <div className="form-group">
                <button className="btn btn-primary" onClick={onRunDefault} disabled={loading}>
                    {loading ? "Processing..." : "Chunk Default Document"}
                </button>
            </div>

            <div className="border-t border-border pt-4 mt-4">
                <div className="form-group">
                    <label className="label">Upload Custom Specification (.txt)</label>
                    <input
                        type="file"
                        className="input"
                        accept=".txt"
                        onChange={(e) => onFileChange(e.target.files?.[0] || null)}
                    />
                </div>

                <div className="form-group">
                    <label className="label">Regex Delimiter Pattern</label>
                    <textarea
                        className="textarea"
                        rows={2}
                        value={regexText}
                        onChange={(e) => setRegexText(e.target.value)}
                        placeholder="e.g. (?<=--PAGE\\s+\\d+\\s+END--)"
                    />
                </div>

                <button className="btn btn-primary" onClick={onRunUpload} disabled={loading}>
                    {loading ? "Uploading & Partitioning..." : "Process Uploaded File"}
                </button>
            </div>

            {error && <div className="error-msg">{error}</div>}
        </div>
    );
}
