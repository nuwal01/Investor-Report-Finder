function ResultsDisplay({ results }) {
    const { query, reports, count, message, resolved_company } = results

    // Determine display name for the company
    const getCompanyDisplay = () => {
        if (resolved_company) {
            return `${resolved_company.company_name} (${resolved_company.ticker})`
        } else if (query.ticker) {
            return query.ticker
        }
        return 'Unknown Company'
    }

    if (count === 0) {
        return (
            <div className="results">
                <div className="results-header">
                    <h2>Search Results</h2>
                    <p className="query-info">
                        <strong>{getCompanyDisplay()}</strong> • {query.report_type} reports •
                        {query.start_year} - {query.end_year}
                    </p>
                </div>

                <div className="empty-state">
                    <p>📄 {message}</p>
                    <small>
                        This could be because:
                        <ul>
                            <li>The company's IR page blocks scraping (robots.txt)</li>
                            <li>No reports match your search criteria</li>
                            <li>The IR page has a non-standard structure</li>
                        </ul>
                    </small>
                </div>
            </div>
        )
    }

    return (
        <div className="results">
            <div className="results-header">
                <h2>✅ Found {count} Report{count !== 1 ? 's' : ''}</h2>
                <p className="query-info">
                    <strong>{getCompanyDisplay()}</strong>
                    {' • '}
                    {query.report_type} reports • {query.start_year} - {query.end_year}
                </p>
            </div>

            <div className="reports-table">
                <table>
                    <thead>
                        <tr>
                            <th>Year</th>
                            <th>Type</th>
                            <th>Title</th>
                            <th>Quarter</th>
                            <th>Source</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {reports.map((report, index) => (
                            <tr key={index}>
                                <td className="year-cell">{report.year}</td>
                                <td className="type-cell">
                                    <span className={`badge badge-${report.type}`}>
                                        {report.type.toUpperCase()}
                                    </span>
                                </td>
                                <td className="title-cell">
                                    <div className="report-title">{report.title}</div>
                                    <div className="report-url" style={{ fontSize: '0.8em', color: '#666', marginTop: '4px', wordBreak: 'break-all' }}>
                                        {report.url}
                                    </div>
                                </td>
                                <td className="quarter-cell">
                                    {report.quarter && <span className="quarter-badge">{report.quarter}</span>}
                                </td>
                                <td className="source-cell">
                                    {report.source && <span className="source-badge">{report.source}</span>}
                                </td>
                                <td className="action-cell">
                                    <a
                                        href={report.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="btn btn-small"
                                    >
                                        📑 Open PDF
                                    </a>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    )
}

export default ResultsDisplay
