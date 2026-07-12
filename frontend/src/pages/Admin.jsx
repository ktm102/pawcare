import React, { useEffect, useState, useCallback } from "react";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from "@/components/ui/dropdown-menu";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import { Users, PawPrint, ChatCircleDots, Stethoscope, TrendUp, Crown, DotsThreeVertical, Gift, Trash } from "@phosphor-icons/react";

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
  const [toDelete, setToDelete] = useState(null);

  const load = useCallback(async () => {
    try {
      const [s, u] = await Promise.all([api.get("/admin/stats"), api.get("/admin/users")]);
      setStats(s.data);
      setUsers(u.data);
    } catch (e) {
      // handled by route guard
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const grant = async (userId, plan) => {
    try {
      await api.post(`/admin/users/${userId}/grant-premium`, { plan });
      toast.success("Premium regalato 🎁");
      load();
    } catch (e) { toast.error("Operazione non riuscita"); }
  };

  const revoke = async (userId) => {
    try {
      await api.post(`/admin/users/${userId}/revoke-premium`);
      toast.success("Premium rimosso");
      load();
    } catch (e) { toast.error("Operazione non riuscita"); }
  };

  const confirmDelete = async () => {
    if (!toDelete) return;
    try {
      await api.delete(`/admin/users/${toDelete.user_id}`);
      toast.success("Account eliminato");
      setToDelete(null);
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Eliminazione non riuscita");
      setToDelete(null);
    }
  };

  const premiumLabel = (u) => {
    if (!u.premium) return null;
    if (u.premium_until && u.premium_until.startsWith("2099")) return "illimitato";
    return u.premium_until ? `fino al ${new Date(u.premium_until).toLocaleDateString("it-IT")}` : "attivo";
  };

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
          <StatCard icon={Crown} label="Utenti Premium" value={stats.premium_users ?? 0} />
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
          <p className="text-sm text-muted-foreground">Gestisci gli account: regala Premium, rimuovilo o elimina gli account demo.</p>
        </div>
        <div className="overflow-x-auto">
          <Table data-testid="admin-users-table">
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Accesso</TableHead>
                <TableHead>Premium</TableHead>
                <TableHead>Registrato</TableHead>
                <TableHead className="text-center">Animali</TableHead>
                <TableHead className="text-center">Chat</TableHead>
                <TableHead className="text-right">Azioni</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((u) => (
                <TableRow key={u.user_id} data-testid="admin-user-row">
                  <TableCell className="font-medium">{u.name || "—"}{u.role === "admin" && <Badge className="ml-2" variant="secondary">admin</Badge>}</TableCell>
                  <TableCell className="text-muted-foreground">{u.email}</TableCell>
                  <TableCell><Badge variant="secondary">{u.auth_provider === "google" ? "Google" : "Email"}</Badge></TableCell>
                  <TableCell>
                    {u.premium
                      ? <Badge className="bg-accent text-accent-foreground gap-1"><Crown size={12} weight="fill" /> {premiumLabel(u)}</Badge>
                      : <span className="text-muted-foreground text-sm">Gratuito</span>}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{u.created_at ? new Date(u.created_at).toLocaleDateString("it-IT") : "—"}</TableCell>
                  <TableCell className="text-center">{u.pet_count}</TableCell>
                  <TableCell className="text-center">{u.chat_count}</TableCell>
                  <TableCell className="text-right">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" data-testid={`user-actions-${u.user_id}`}><DotsThreeVertical size={20} weight="bold" /></Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => grant(u.user_id, "monthly")} data-testid="gift-monthly"><Gift size={16} className="mr-2" /> Regala Premium 1 mese</DropdownMenuItem>
                        <DropdownMenuItem onClick={() => grant(u.user_id, "yearly")}><Gift size={16} className="mr-2" /> Regala Premium 1 anno</DropdownMenuItem>
                        <DropdownMenuItem onClick={() => grant(u.user_id, "lifetime")}><Crown size={16} className="mr-2" /> Premium illimitato (gratis)</DropdownMenuItem>
                        {u.premium && <DropdownMenuItem onClick={() => revoke(u.user_id)}>Rimuovi Premium</DropdownMenuItem>}
                        {u.role !== "admin" && (
                          <>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem className="text-destructive" onClick={() => setToDelete(u)} data-testid="delete-user"><Trash size={16} className="mr-2" /> Elimina account</DropdownMenuItem>
                          </>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Card>

      <AlertDialog open={!!toDelete} onOpenChange={(o) => !o && setToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Eliminare l'account?</AlertDialogTitle>
            <AlertDialogDescription>
              Stai per eliminare <strong>{toDelete?.email}</strong> e tutti i suoi dati (animali, documenti, chat). L'azione è irreversibile.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annulla</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} data-testid="confirm-delete-user">Elimina</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
