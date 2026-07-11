import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import PetDialog from "@/components/PetDialog";
import { checkReminders } from "@/lib/push";
import { Plus, Dog, Cat, Syringe, ShieldCheck, CalendarBlank, WarningCircle } from "@phosphor-icons/react";

function DueBadge({ days }) {
  if (days < 0) return <Badge variant="destructive" data-testid="due-badge">Scaduto</Badge>;
  if (days <= 7) return <Badge className="bg-destructive/90" data-testid="due-badge">{days === 0 ? "Oggi" : `Tra ${days}g`}</Badge>;
  if (days <= 30) return <Badge className="bg-accent text-accent-foreground" data-testid="due-badge">Tra {days}g</Badge>;
  return <Badge variant="secondary" data-testid="due-badge">Tra {days}g</Badge>;
}

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [pets, setPets] = useState([]);
  const [upcoming, setUpcoming] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [p, u] = await Promise.all([api.get("/pets"), api.get("/dashboard/upcoming")]);
      setPets(p.data);
      setUpcoming(u.data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { checkReminders(); }, []);

  return (
    <div className="space-y-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs tracking-[0.2em] uppercase font-bold text-muted-foreground mb-1">Ciao {user?.name?.split(" ")[0]}</p>
          <h1 className="font-heading text-3xl sm:text-4xl font-extrabold tracking-tighter">I tuoi animali</h1>
        </div>
        <Button className="rounded-full gap-2" onClick={() => setDialogOpen(true)} data-testid="add-pet-button">
          <Plus size={18} weight="bold" /> Aggiungi animale
        </Button>
      </div>

      {/* Upcoming */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <CalendarBlank size={22} weight="duotone" className="text-primary" />
          <h2 className="font-heading text-xl font-bold">Prossime scadenze</h2>
        </div>
        {upcoming.length === 0 ? (
          <Card className="p-6 border-dashed text-muted-foreground text-sm flex items-center gap-2" data-testid="no-upcoming">
            <ShieldCheck size={20} weight="duotone" className="text-primary" />
            Nessuna scadenza imminente. Ottimo lavoro!
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {upcoming.slice(0, 6).map((item, i) => (
              <Card
                key={i}
                className="p-5 border-border hover:-translate-y-1 hover:shadow-sm transition-[transform,box-shadow] cursor-pointer"
                onClick={() => navigate(`/pet/${item.pet_id}`)}
                data-testid="upcoming-item"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    {item.type === "vaccine" ? <Syringe size={20} weight="duotone" className="text-primary" /> : <ShieldCheck size={20} weight="duotone" className="text-accent" />}
                    <span className="text-xs uppercase tracking-wider text-muted-foreground">{item.type === "vaccine" ? "Vaccino" : "Antiparassitario"}</span>
                  </div>
                  <DueBadge days={item.days_left} />
                </div>
                <h3 className="font-heading font-bold text-lg mt-2">{item.title}</h3>
                <p className="text-sm text-muted-foreground">{item.pet_name} · {new Date(item.due_date).toLocaleDateString("it-IT")}</p>
              </Card>
            ))}
          </div>
        )}
      </section>

      {/* Pets */}
      <section>
        {loading ? (
          <p className="text-muted-foreground">Caricamento...</p>
        ) : pets.length === 0 ? (
          <Card className="p-10 border-dashed text-center" data-testid="empty-pets">
            <Dog size={48} weight="duotone" className="text-primary mx-auto mb-3" />
            <h3 className="font-heading font-bold text-lg">Nessun animale ancora</h3>
            <p className="text-muted-foreground text-sm mb-4">Aggiungi il tuo primo amico a quattro zampe per iniziare.</p>
            <Button className="rounded-full gap-2" onClick={() => setDialogOpen(true)} data-testid="add-first-pet-button">
              <Plus size={18} weight="bold" /> Aggiungi animale
            </Button>
          </Card>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {pets.map((pet) => {
              const Icon = pet.species === "dog" ? Dog : Cat;
              return (
                <Card
                  key={pet.id}
                  className="overflow-hidden border-border hover:-translate-y-1 hover:shadow-sm transition-[transform,box-shadow] cursor-pointer"
                  onClick={() => navigate(`/pet/${pet.id}`)}
                  data-testid={`pet-card-${pet.id}`}
                >
                  <div className="h-40 bg-muted flex items-center justify-center overflow-hidden">
                    {pet.photo ? (
                      <img src={pet.photo} alt={pet.name} className="w-full h-full object-cover" />
                    ) : (
                      <Icon size={56} weight="duotone" className="text-primary/40" />
                    )}
                  </div>
                  <div className="p-5">
                    <div className="flex items-center justify-between">
                      <h3 className="font-heading font-bold text-xl">{pet.name}</h3>
                      <Icon size={22} weight="duotone" className="text-primary" />
                    </div>
                    <p className="text-sm text-muted-foreground">{pet.breed} · {pet.age} {pet.age === 1 ? "anno" : "anni"}</p>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </section>

      <PetDialog open={dialogOpen} onOpenChange={setDialogOpen} onSaved={load} pet={null} />
    </div>
  );
}
