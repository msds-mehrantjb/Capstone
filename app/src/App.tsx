import React, { useEffect, useState } from "react";
import Dashboard from "./pages/Dashboard";
import ScopeContext from "./pages/ScopeContext";

type RouteKey = "dashboard" | "scope";

function getRouteFromHash(): RouteKey {
  const h = (window.location.hash || "").toLowerCase();
  if (h.startsWith("#/scope")) return "scope";
  return "dashboard";
}

export default function App() {
  const [route, setRoute] = useState<RouteKey>(() => {
    if (!window.location.hash) window.location.hash = "#/dashboard";
    return getRouteFromHash();
  });

  useEffect(() => {
    const onHash = () => setRoute(getRouteFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  return route === "scope" ? <ScopeContext /> : <Dashboard />;
}
