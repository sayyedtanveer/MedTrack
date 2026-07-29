import { Navigate, Outlet } from "react-router-dom";
import { useIsPlatformAdmin } from "@/hooks/useIsPlatformAdmin";

export function PlatformRoute() {
  const isPlatformAdmin = useIsPlatformAdmin();

  if (!isPlatformAdmin) {
    return <Navigate to="/forbidden" replace />;
  }

  return <Outlet />;
}
