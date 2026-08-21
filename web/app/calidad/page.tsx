import { getSystemQuality } from "@/lib/api";

export default async function CalidadPage() {
  const payload = await getSystemQuality();

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Calidad</h1>
          <p className="page-subtitle">
            Señales operativas para confiar en el dataset antes de tomar decisiones comerciales o analíticas.
          </p>
        </div>
      </div>

      <section className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Filas evaluadas</div>
          <div className="stat-value">{payload.summary.total_rows.toLocaleString("es-CL")}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Issues</div>
          <div className="stat-value">{payload.summary.issues_count.toLocaleString("es-CL")}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Warnings</div>
          <div className="stat-value">{(payload.summary.severity_counts.warning ?? 0).toLocaleString("es-CL")}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Critical</div>
          <div className="stat-value">{(payload.summary.severity_counts.critical ?? 0).toLocaleString("es-CL")}</div>
        </div>
      </section>

      <section className="panel">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Tipo</th>
                <th>Severidad</th>
                <th>Cantidad</th>
                <th>Descripción</th>
              </tr>
            </thead>
            <tbody>
              {payload.issues.map((issue) => (
                <tr key={issue.issue_type}>
                  <td>{issue.issue_type}</td>
                  <td>{issue.severity}</td>
                  <td>{issue.count}</td>
                  <td style={{ whiteSpace: "normal" }}>{issue.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
