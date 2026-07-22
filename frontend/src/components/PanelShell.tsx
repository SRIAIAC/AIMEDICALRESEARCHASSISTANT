import type { ReactNode } from "react";

export function PanelShell({
  icon,
  title,
  description,
  children,
}: {
  icon: string;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <section className="agent-panel">
      <header className="agent-panel-header">
        <span className="agent-panel-icon" aria-hidden="true">
          {icon}
        </span>
        <div>
          <h2>{title}</h2>
          <p className="panel-description">{description}</p>
        </div>
      </header>
      <div className="panel-body">{children}</div>
    </section>
  );
}
