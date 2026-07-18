import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";

import { AppRouter } from "./router";

export function App() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 15_000 }, mutations: { retry: false } } });
  return <QueryClientProvider client={client}><BrowserRouter><AppRouter /></BrowserRouter></QueryClientProvider>;
}
