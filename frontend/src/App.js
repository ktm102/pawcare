import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { Toaster } from "@/components/ui/sonner";
import AuthCallback from "@/components/AuthCallback";
import Auth from "@/pages/Auth";
import Dashboard from "@/pages/Dashboard";
import PetDetail from "@/pages/PetDetail";
import Guides from "@/pages/Guides";
import Assistant from "@/pages/Assistant";
import Calendar from "@/pages/Calendar";
import Admin from "@/pages/Admin";
import Subscription from "@/pages/Subscription";
import Layout from "@/components/Layout";
import { PawPrint } from "@phosphor-icons/react";

function LoadingScreen() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4">
      <PawPrint size={48} weight="duotone" className="text-primary animate-pulse" />
      <p className="text-muted-foreground">Caricamento...</p>
    </div>
  );
}

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  if (!user) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
}

function PublicOnly({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  if (user) return <Navigate to="/dashboard" replace />;
  return children;
}

function AdminRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "admin") return <Navigate to="/dashboard" replace />;
  return <Layout>{children}</Layout>;
}

function AppRouter() {
  const location = useLocation();
  if (location.hash?.includes("session_id=")) {
    return <AuthCallback />;
  }
  return (
    <Routes>
      <Route path="/login" element={<PublicOnly><Auth /></PublicOnly>} />
      <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
      <Route path="/pet/:petId" element={<Protected><PetDetail /></Protected>} />
      <Route path="/calendario" element={<Protected><Calendar /></Protected>} />
      <Route path="/abbonamento" element={<Protected><Subscription /></Protected>} />
      <Route path="/guide" element={<Protected><Guides /></Protected>} />
      <Route path="/assistente" element={<Protected><Assistant /></Protected>} />
      <Route path="/admin" element={<AdminRoute><Admin /></AdminRoute>} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <AppRouter />
          <Toaster position="top-right" richColors />
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}

export default App;
