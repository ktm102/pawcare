import React, { useEffect, useState } from "react";
import { useLocation, useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { toast } from "sonner";
import { pushSupported, getSubscriptionStatus, subscribeToPush, unsubscribeFromPush } from "@/lib/push";
import { PawPrint, House, BookOpen, ChatCircleDots, SignOut, Bell, BellSlash, CalendarBlank } from "@phosphor-icons/react";

const nav = [
  { to: "/dashboard", label: "Dashboard", icon: House },
  { to: "/calendario", label: "Calendario", icon: CalendarBlank },
  { to: "/guide", label: "Guide", icon: BookOpen },
  { to: "/assistente", label: "Assistente AI", icon: ChatCircleDots },
];

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [notifOn, setNotifOn] = useState(false);
  const [notifBusy, setNotifBusy] = useState(false);
  const supported = pushSupported();

  useEffect(() => {
    if (supported) getSubscriptionStatus().then(setNotifOn).catch(() => {});
  }, [supported]);

  const toggleNotif = async () => {
    setNotifBusy(true);
    try {
      if (notifOn) {
        await unsubscribeFromPush();
        setNotifOn(false);
        toast.success("Notifiche disattivate");
      } else {
        await subscribeToPush();
        setNotifOn(true);
        toast.success("Notifiche attivate! Ti avviseremo delle prossime scadenze.");
      }
    } catch (e) {
      toast.error(e.message || "Impossibile gestire le notifiche");
    } finally {
      setNotifBusy(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen grain flex flex-col">
      <header className="sticky top-0 z-50 bg-card/95 backdrop-blur-md border-b border-border">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <Link to="/dashboard" className="flex items-center gap-2" data-testid="brand-logo">
            <PawPrint size={28} weight="duotone" className="text-primary" />
            <span className="font-heading font-extrabold text-xl tracking-tight">PawCare</span>
          </Link>
          <nav className="hidden md:flex items-center gap-1">
            {nav.map((n) => {
              const active = location.pathname.startsWith(n.to);
              const Icon = n.icon;
              return (
                <Link
                  key={n.to}
                  to={n.to}
                  data-testid={`nav-${n.to.replace("/", "")}`}
                  className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                    active ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted"
                  }`}
                >
                  <Icon size={18} weight={active ? "fill" : "regular"} />
                  {n.label}
                </Link>
              );
            })}
          </nav>
          <div className="flex items-center gap-3">
            {supported && (
              <Button
                variant={notifOn ? "default" : "ghost"}
                size="icon"
                className="rounded-full"
                onClick={toggleNotif}
                disabled={notifBusy}
                data-testid="notifications-toggle"
                title={notifOn ? "Disattiva notifiche" : "Attiva notifiche"}
              >
                {notifOn ? <Bell size={20} weight="fill" /> : <BellSlash size={20} />}
              </Button>
            )}
            <Avatar className="h-9 w-9 border border-border">
              <AvatarImage src={user?.picture} />
              <AvatarFallback className="bg-secondary text-secondary-foreground text-sm">
                {user?.name?.[0]?.toUpperCase() || "U"}
              </AvatarFallback>
            </Avatar>
            <Button variant="ghost" size="icon" onClick={handleLogout} data-testid="logout-button" title="Esci">
              <SignOut size={20} />
            </Button>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-8 relative z-10">{children}</main>

      <nav className="md:hidden sticky bottom-0 z-50 bg-card border-t border-border grid grid-cols-4">
        {nav.map((n) => {
          const active = location.pathname.startsWith(n.to);
          const Icon = n.icon;
          return (
            <Link key={n.to} to={n.to} className={`flex flex-col items-center gap-1 py-3 text-xs ${active ? "text-primary" : "text-muted-foreground"}`}>
              <Icon size={22} weight={active ? "fill" : "regular"} />
              {n.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
