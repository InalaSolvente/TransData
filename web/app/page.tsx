import Link from "next/link";

import { getFilters, getListing, type ListingItem } from "@/lib/api";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

function formatDate(value: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleDateString("es-CL");
}

function formatMoney(value: number | null, moneda: string) {
  if (value === null || Number.isNaN(value)) return "-";
  return `${moneda || "CLP"} ${Math.round(value).toLocaleString("es-CL")}`;
}

function buildSearchString(params: Record<string, string | string[] | undefined>) {
  const search = new URLSearchParams();
  for (const [key, raw] of Object.entries(params)) {
    if (Array.isArray(raw)) {
      raw.forEach((item) => {
        if (item) search.append(key, item);
      });
    } else if (raw) {
      search.set(key, raw);
    }
  }
  return search.toString();
}

function statusBadge(item: ListingItem) {
  const cls =
    item.estado_bucket === "adjudicada"
      ? "badge success"
      : item.estado_bucket === "publicada"
        ? "badge warning"
        : item.estado_bucket === "desierta"
          ? "badge danger"
          : "badge";
  return <span className={cls}>{item.estado_bucket || item.estado}</span>;
}

export default async function LicitacionesPage({
  searchParams
}: {
  searchParams: SearchParams;
}) {
  const params = await searchParams;
  const queryString = buildSearchString(params);
  const [listing, filters] = await Promise.all([getListing(queryString), getFilters()]);

  const currentPage = Number(params.page ?? listing.pagination.page);
  const pageSize = Number(params.page_size ?? listing.pagination.page_size);
  const hasPrev = currentPage > 1;
  const hasNext = currentPage < listing.pagination.total_pages;

  const buildPageHref = (page: number) => {
    const nextParams = new URLSearchParams(queryString);
    nextParams.set("page", String(page));
    nextParams.set("page_size", String(pageSize));
    return `/?${nextParams.toString()}`;
  };

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Explorador de Licitaciones</h1>
          <p className="page-subtitle">
            Base curada desde <code>transport_master_core</code> para encontrar oportunidades, abrir fichas y priorizar seguimiento comercial.
          </p>
        </div>
      </div>

      <section className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Resultados totales</div>
          <div className="stat-value">{listing.pagination.total_results.toLocaleString("es-CL")}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Página actual</div>
          <div className="stat-value">{currentPage}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Tamaño página</div>
          <div className="stat-value">{pageSize}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Sort activo</div>
          <div className="stat-value">{listing.sort.field}</div>
        </div>
      </section>

      <section className="panel">
        <form className="filters-form" action="/" method="get">
          <div className="field">
            <label htmlFor="q">Búsqueda</label>
            <input id="q" name="q" defaultValue={typeof params.q === "string" ? params.q : ""} placeholder="Nombre, comprador o código" />
          </div>
          <div className="field">
            <label htmlFor="estado_bucket">Estado</label>
            <select id="estado_bucket" name="estado_bucket" defaultValue={typeof params.estado_bucket === "string" ? params.estado_bucket : ""}>
              <option value="">Todos</option>
              {filters.data.estado_bucket?.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="region">Región</label>
            <select id="region" name="region" defaultValue={typeof params.region === "string" ? params.region : ""}>
              <option value="">Todas</option>
              {filters.data.region?.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="revision_segmento">Segmento</label>
            <select
              id="revision_segmento"
              name="revision_segmento"
              defaultValue={typeof params.revision_segmento === "string" ? params.revision_segmento : ""}
            >
              <option value="">Todos</option>
              {filters.data.revision_segmento?.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="revision_prioridad">Prioridad</label>
            <select
              id="revision_prioridad"
              name="revision_prioridad"
              defaultValue={typeof params.revision_prioridad === "string" ? params.revision_prioridad : ""}
            >
              <option value="">Todas</option>
              {filters.data.revision_prioridad?.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="periodo_publicacion">Periodo</label>
            <select
              id="periodo_publicacion"
              name="periodo_publicacion"
              defaultValue={typeof params.periodo_publicacion === "string" ? params.periodo_publicacion : ""}
            >
              <option value="">Todos</option>
              {filters.data.periodo_publicacion?.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="sort">Orden</label>
            <select id="sort" name="sort" defaultValue={typeof params.sort === "string" ? params.sort : "fecha_publicacion:desc"}>
              <option value="fecha_publicacion:desc">Publicación reciente</option>
              <option value="fecha_cierre:asc">Cierre próximo</option>
              <option value="monto_estimado:desc">Monto estimado</option>
              <option value="monto_adjudicado:desc">Monto adjudicado</option>
              <option value="transport_score:desc">Score transporte</option>
            </select>
          </div>
          <div className="button-row">
            <input type="hidden" name="page" value="1" />
            <input type="hidden" name="page_size" value={String(pageSize)} />
            <button className="button primary" type="submit">
              Aplicar filtros
            </button>
            <Link className="button" href="/">
              Limpiar
            </Link>
          </div>
        </form>
      </section>

      <section className="panel">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Licitación</th>
                <th>Estado</th>
                <th>Fechas</th>
                <th>Comprador</th>
                <th>Segmento</th>
                <th>Prioridad</th>
                <th>Monto</th>
              </tr>
            </thead>
            <tbody>
              {listing.data.map((item) => (
                <tr key={item.codigo_licitacion}>
                  <td>
                    <div className="table-title">
                      <Link href={`/licitaciones/${item.codigo_licitacion}`}>{item.nombre}</Link>
                    </div>
                    <div className="secondary-text">{item.codigo_licitacion}</div>
                  </td>
                  <td>{statusBadge(item)}</td>
                  <td>
                    <div>Pub: {formatDate(item.fecha_publicacion)}</div>
                    <div className="secondary-text">Cie: {formatDate(item.fecha_cierre)}</div>
                  </td>
                  <td>
                    <div>{item.comprador_nombre}</div>
                    <div className="secondary-text">
                      {item.region} {item.comuna ? `· ${item.comuna}` : ""}
                    </div>
                  </td>
                  <td>{item.revision_segmento || "-"}</td>
                  <td>{item.revision_prioridad || "-"}</td>
                  <td>{formatMoney(item.monto_estimado, item.moneda)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel pagination">
        <div className="secondary-text">
          Página {listing.pagination.page} de {listing.pagination.total_pages}
        </div>
        <div className="button-row">
          {hasPrev ? (
            <Link className="button" href={buildPageHref(currentPage - 1)}>
              Anterior
            </Link>
          ) : (
            <span className="button secondary-text">Anterior</span>
          )}
          {hasNext ? (
            <Link className="button primary" href={buildPageHref(currentPage + 1)}>
              Siguiente
            </Link>
          ) : (
            <span className="button secondary-text">Siguiente</span>
          )}
        </div>
      </section>
    </>
  );
}
