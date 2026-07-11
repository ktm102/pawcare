import React, { useState, useEffect } from "react";
import api from "@/lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";

const empty = { name: "", species: "dog", breed: "", birth_date: "", sex: "M", weight: "", photo: "" };

export default function PetDialog({ open, onOpenChange, onSaved, pet }) {
  const [form, setForm] = useState(empty);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (pet) {
      setForm({ ...empty, ...pet, weight: pet.weight ?? "" });
    } else {
      setForm(empty);
    }
  }, [pet, open]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const onPhoto = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onloadend = () => set("photo", reader.result);
    reader.readAsDataURL(file);
  };

  const save = async () => {
    if (!form.name || !form.breed || !form.birth_date) {
      toast.error("Compila nome, razza e data di nascita");
      return;
    }
    setBusy(true);
    try {
      const payload = {
        name: form.name,
        species: form.species,
        breed: form.breed,
        birth_date: form.birth_date,
        sex: form.sex,
        weight: form.weight ? parseFloat(form.weight) : null,
        photo: form.photo || null,
      };
      if (pet) {
        await api.put(`/pets/${pet.id}`, payload);
        toast.success("Animale aggiornato");
      } else {
        await api.post("/pets", payload);
        toast.success("Animale aggiunto");
      }
      onSaved();
      onOpenChange(false);
    } catch (e) {
      toast.error("Errore nel salvataggio");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="font-heading">{pet ? "Modifica animale" : "Nuovo animale"}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="h-16 w-16 rounded-full bg-muted overflow-hidden border border-border flex items-center justify-center">
              {form.photo ? <img src={form.photo} alt="anteprima" className="h-full w-full object-cover" /> : <span className="text-xs text-muted-foreground">Foto</span>}
            </div>
            <div>
              <Label htmlFor="photo" className="cursor-pointer text-sm text-primary hover:underline">Carica foto</Label>
              <Input id="photo" type="file" accept="image/*" onChange={onPhoto} className="hidden" data-testid="pet-photo-input" />
            </div>
          </div>
          <div>
            <Label>Nome</Label>
            <Input value={form.name} onChange={(e) => set("name", e.target.value)} data-testid="pet-name-input" className="mt-1" placeholder="Fido" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Specie</Label>
              <Select value={form.species} onValueChange={(v) => set("species", v)}>
                <SelectTrigger className="mt-1" data-testid="pet-species-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="dog">Cane</SelectItem>
                  <SelectItem value="cat">Gatto</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Sesso</Label>
              <Select value={form.sex} onValueChange={(v) => set("sex", v)}>
                <SelectTrigger className="mt-1" data-testid="pet-sex-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="M">Maschio</SelectItem>
                  <SelectItem value="F">Femmina</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div>
            <Label>Razza</Label>
            <Input value={form.breed} onChange={(e) => set("breed", e.target.value)} data-testid="pet-breed-input" className="mt-1" placeholder="Labrador" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Data di nascita</Label>
              <Input type="date" value={form.birth_date} onChange={(e) => set("birth_date", e.target.value)} data-testid="pet-birthdate-input" className="mt-1" />
            </div>
            <div>
              <Label>Peso (kg)</Label>
              <Input type="number" step="0.1" value={form.weight} onChange={(e) => set("weight", e.target.value)} data-testid="pet-weight-input" className="mt-1" placeholder="12.5" />
            </div>
          </div>
          <Button onClick={save} disabled={busy} className="w-full rounded-full" data-testid="save-pet-button">
            {busy ? "Salvataggio..." : "Salva"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
