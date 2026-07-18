import { useQuery } from "@tanstack/react-query";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { ApiRequestError, productApi } from "../api/client";
import { AsyncState } from "./AsyncState";

export function SessionGuard() {
  const location = useLocation();
  const session = useQuery({ queryKey: ["session"], queryFn: () => productApi.getSession(), staleTime: 60_000 });
  if (session.error instanceof ApiRequestError && session.error.status === 401) {
    return <Navigate replace state={{ from: `${location.pathname}${location.search}` }} to="/login" />;
  }
  return <AsyncState error={session.error} loading={session.isPending}><Outlet /></AsyncState>;
}
