import { AlertTriangle, LoaderCircle } from "lucide-react";
import type { ReactNode } from "react";

export function AsyncState({ loading, error, children }: { loading: boolean; error?: Error | null; children: ReactNode }) {
  if (loading) {
    return <div className="async-state"><LoaderCircle aria-hidden="true" className="spin" size={18} />正在读取...</div>;
  }
  if (error) {
    return <div className="async-state error" role="alert"><AlertTriangle aria-hidden="true" size={18} />{error.message}</div>;
  }
  return <>{children}</>;
}
