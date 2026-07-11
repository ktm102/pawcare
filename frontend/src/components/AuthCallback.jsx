import React, { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { PawPrint } from "@phosphor-icons/react";

export default function AuthCallback() {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const hash = window.location.hash;
    const match = hash.match(/session_id=([^&]+)/);
    const sessionId = match ? match[1] : null;

    const run = async () => {
      if (!sessionId) {
        navigate("/login");
        return;
      }
      try {
        const { data } = await api.post(
          "/auth/google/session",
          {},
          { headers: { "X-Session-ID": sessionId } }
        );
        setUser(data.user);
        window.history.replaceState(null, "", "/dashboard");
        navigate("/dashboard", { state: { user: data.user } });
      } catch (e) {
        navigate("/login");
      }
    };
    run();
  }, [navigate, setUser]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4">
      <PawPrint size={48} weight="duotone" className="text-primary animate-pulse" />
      <p className="text-muted-foreground">Accesso in corso...</p>
    </div>
  );
}
