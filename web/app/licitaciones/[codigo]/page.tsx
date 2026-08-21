import Link from "next/link";
import { notFound } from "next/navigation";

import { getDetail } from "@/lib/api";

function renderValue(value: string | number | boolean | null | undefined) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "boolean") return value ? "Sí" : "No";
  return String(value);
}

export default async function LicitacionDetailPage({
  params
}: {
  params: Promise<{ codigo: string }>;
}) {
  const { codigo } = await params;

  try {
    const detail = await getDetail(codigo);
    const item = detail.data;

    return (
      <>
        <div className="page-header">
          <div>
            <Link href="/" className="secondary-text">
              ← Volver a licitaciones
            </Link>
            <h1 className="page-title">{item.nombre}</h1>
            <p className="page-subtitle">
              {item.codigo_licitacion} · {item.estado_bucket} · {item.region}
            </p>
          </div>
        </div>

        <section className="meta-row">
          <div className="meta-item">
            <div className="meta-label">Comprador</div>
            <div className="meta-value">{renderValue(item.comprador_nombre)}</div>
          </div>
          <div className="meta-item">
            <div className="meta-label">RUT comprador</div>
            <div className="meta-value">{renderValue(item.comprador_rut)}</div>
          </div>
          <div className="meta-item">
            <div className="meta-label">Unidad</div>
            <div className="meta-value">{renderValue(item.unidad_nombre)}</div>
          </div>
          <div className="meta-item">
            <div className="meta-label">Ubicación</div>
            <div className="meta-value">
              {renderValue(item.region)} / {renderValue(item.comuna)}
            </div>
          </div>
          <div className="meta-item">
            <div className="meta-label">Monto estimado</div>
            <div className="meta-value">
              {renderValue(item.moneda)} {renderValue(item.monto_estimado)}
            </div>
          </div>
          <div className="meta-item">
            <div className="meta-label">Monto adjudicado</div>
            <div className="meta-value">
              {renderValue(item.moneda)} {renderValue(item.monto_adjudicado)}
            </div>
          </div>
          <div className="meta-item">
            <div className="meta-label">Proveedor adjudicado</div>
            <div className="meta-value">{renderValue(item.proveedor_adjudicado_nombre)}</div>
          </div>
          <div className="meta-item">
            <div className="meta-label">RUT proveedor</div>
            <div className="meta-value">{renderValue(item.proveedor_adjudicado_rut)}</div>
          </div>
          <div className="meta-item">
            <div className="meta-label">Clasificación</div>
            <div className="meta-value">
              Score {renderValue(item.transport_score)} · {renderValue(item.transport_rule)}
            </div>
          </div>
          <div className="meta-item">
            <div className="meta-label">Revisión manual</div>
            <div className="meta-value">
              {renderValue(item.revision_decision)} / {renderValue(item.revision_segmento)} / {renderValue(item.revision_prioridad)}
            </div>
          </div>
          <div className="meta-item">
            <div className="meta-label">Refresh pendiente</div>
            <div className="meta-value">{renderValue(item.requiere_refresh_adjudicacion)}</div>
          </div>
          <div className="meta-item">
            <div className="meta-label">Última revisión</div>
            <div className="meta-value">{renderValue(item.ultima_revision)}</div>
          </div>
        </section>

        <section className="panel-grid">
          <div className="panel">
            <div className="meta-label">Descripción</div>
            <div className="description-box">{renderValue(item.descripcion)}</div>
          </div>
          <div className="panel">
            <div className="meta-label">Ficha original</div>
            {item.url_ficha ? (
              <a className="button primary" href={item.url_ficha} target="_blank" rel="noreferrer">
                Abrir ficha de Mercado Público
              </a>
            ) : (
              <div className="secondary-text">No disponible</div>
            )}
          </div>
        </section>
      </>
    );
  } catch {
    notFound();
  }
}
