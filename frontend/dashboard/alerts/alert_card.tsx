export type AlertCardProps = { id: string; message: string; level?: 'info'|'warn'|'error'; ts?: string };
export const AlertCard = (p: AlertCardProps) => { return <div className={`alert ${p.level||'info'}`} data-id={p.id}>{p.message}</div>; };
