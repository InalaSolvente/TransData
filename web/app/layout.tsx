import "./globals.css";
import Link from "next/link";
import type { ReactNode } from "react";

export const metadata = {
  title: "TransData",
  description: "Explorador web de licitaciones de transporte"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <body>
        <div className="app-shell">
          <aside className="sidebar">
            <div className="brand">TransData</div>
            <div className="nav-group">
              <Link href="/" className="nav-link active">
                Licitaciones
              </Link>
              <Link href="/mercado" className="nav-link">
                Mercado
              </Link>
              <Link href="/calidad" className="nav-link">
                Calidad
              </Link>
            </div>
          </aside>
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
