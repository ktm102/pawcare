import React, { useEffect, useState, useCallback } from "react";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Users, PawPrint, ChatCircleDots, Stethoscope, TrendUp } from "@phosphor-icons/react";

const StatCard = ({ icon: Icon, label, value, hint }) => (
  <Card className="p-5 border-border">
    <div className="flex items-center justify-between">
      <p className="text-xs tracking-[0.15em] uppercase font-bold text-muted-foreground">{label}</p>
      <Icon size={20} weight="duotone" className="text-primary" />
    </div>
    <p className="font-heading text-3xl font-extrabold mt-2">{value}</p>
    {hint && <p className="text-xs text-muted-foreground mt-1">{hint}</p>}
  </Card>
);

export default function Admin() {
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);

  const load = useCallback(async () => {
    try {
      const [s, u] = await Promise.all([api.get("/admin/stats"), api.get("/admin/users")]);
      setStats(s.data);
      setUsers(u.data);
    } catch (e) {
      // access denied or network error — handled by route guard
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-8">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Users size={24} weight="duotone" className="text-primary" />
          <p className="text-xs tracking-[0.2em] uppercase font-bold text-muted-foreground">Amministrazione</p>
        </div>
        <h1 className="font-heading text-3xl sm:text-4xl font-extrabold tracking-tighter">Pannello admin</h1>
      </div>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4" data-testid="admin-stats">
          <StatCard icon={Users} label="Utenti totali" value={stats.total_users} hint={`${stats.google_users} Google · ${stats.email_users} Email`} />
          <StatCard icon={TrendUp} label="Nuovi (7 giorni)" value={stats.new_users_7d} />
          <StatCard icon={PawPrint} label="Animali" value={stats.total_pets} />
          <StatCard icon={Stethoscope} label="Visite" value={stats.total_visits} />
          <StatCard icon={PawPrint} label="Vaccini" value={stats.total_vaccines} />
          <StatCard icon={PawPrint} label="Antiparassitari" value={stats.total_treatments} />
          <StatCard icon={ChatCircleDots} label="Messaggi AI" value={stats.total_chat_messages} />
        </div>
      )}

      <Card className="border-border overflow-hidden">
        <div className="p-5 border-b border-border">
          <h2 className="font-heading text-xl font-bold">Utenti registrati</h2>
        </div>
        <div className="overflow-x-auto">
          <Table data-testid="admin-users-table">
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Accesso</TableHead>
                <TableHead>Registrato</TableHead>
                <TableHead className="text-center">Animali</TableHead>
                <TableHead className="text-center">Chat</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((u) => (
                <TableRow key={u.user_id} data-testid="admin-user-row">
                  <TableCell className="font-medium">{u.name || "—"}{u.role === "admin" && <Badge className="ml-2" variant="secondary">admin</Badge>}</TableCell>
                  <TableCell className="text-muted-foreground">{u.email}</TableCell>
                  <TableCell><Badge variant="secondary">{u.auth_provider === "google" ? "Google" : "Email"}</Badge></TableCell>
                  <TableCell className="text-muted-foreground">{u.created_at ? new Date(u.created_at).toLocaleDateString("it-IT") : "—"}</TableCell>
                  <TableCell className="text-center">{u.pet_count}</TableCell>
                  <TableCell className="text-center">{u.chat_count}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Card>
    </div>
  );
}
