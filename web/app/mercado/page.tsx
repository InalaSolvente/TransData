import { getMarketSummary } from "@/lib/api";

export default async function MercadoPage() {
  const { data } = await getMarketSummary();

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Mercado</h1>
          <p className="page-subtitle">
            Vista resumida del universo sectorial curado. Esta pantalla es una base inicial para comparativas y BI.
          </p>
        </div>
      </div>

      <section className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Licitaciones core</div>
          <div className="stat-value">{data.rows.toLocaleString("es-CL")}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Adjudicaciones capturadas</div>
          <div className="stat-value">{data.adjudicacion_capturada_rows.toLocaleString("es-CL")}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Refresh pendiente</div>
          <div className="stat-value">{data.refresh_pending_rows.toLocaleString("es-CL")}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Rango publicación</div>
          <div className="stat-value">{data.publicacion_min?.slice(0, 10)} → {data.publicacion_max?.slice(0, 10)}</div>
        </div>
      </section>

      <section className="panel">
        <p className="page-subtitle">
          Siguiente iteración: conectar aquí compradores agregados, evolución por periodo, distribución por región y segmentos validados.
        </p>
      </section>
    </>
  );
}
