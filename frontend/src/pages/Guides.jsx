import React, { useEffect, useState, useCallback } from "react";
import api from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { BookOpen, Dog, Cat } from "@phosphor-icons/react";

export default function Guides() {
  const [guides, setGuides] = useState([]);
  const [filter, setFilter] = useState("all");

  const load = useCallback(async () => {
    const params = filter === "all" ? {} : { species: filter };
    const { data } = await api.get("/guides", { params });
    setGuides(data);
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <BookOpen size={24} weight="duotone" className="text-primary" />
            <p className="text-xs tracking-[0.2em] uppercase font-bold text-muted-foreground">Libreria</p>
          </div>
          <h1 className="font-heading text-3xl sm:text-4xl font-extrabold tracking-tighter">Guide su cura e prevenzione</h1>
        </div>
        <div className="flex gap-2">
          <FilterBtn active={filter === "all"} onClick={() => setFilter("all")} label="Tutte" />
          <FilterBtn active={filter === "dog"} onClick={() => setFilter("dog")} label="Cani" icon={Dog} />
          <FilterBtn active={filter === "cat"} onClick={() => setFilter("cat")} label="Gatti" icon={Cat} />
        </div>
      </div>

      <div className="rounded-xl overflow-hidden border border-border">
        <img src="https://images.pexels.com/photos/31961534/pexels-photo-31961534.jpeg" alt="Cura degli animali" className="w-full h-48 object-cover" />
      </div>

      <Accordion type="single" collapsible className="space-y-3">
        {guides.map((g) => {
          const Icon = g.species === "dog" ? Dog : Cat;
          return (
            <AccordionItem key={g.id} value={g.id} className="border border-border rounded-lg px-5 bg-card" data-testid={`guide-${g.id}`}>
              <AccordionTrigger className="hover:no-underline">
                <div className="flex items-center gap-3 text-left">
                  <Icon size={22} weight="duotone" className="text-primary shrink-0" />
                  <span className="font-heading font-bold">{g.title}</span>
                  <Badge variant="secondary" className="ml-1">{g.species === "dog" ? "Cane" : "Gatto"}</Badge>
                </div>
              </AccordionTrigger>
              <AccordionContent className="text-muted-foreground leading-relaxed">{g.content}</AccordionContent>
            </AccordionItem>
          );
        })}
      </Accordion>
    </div>
  );
}

const FilterBtn = ({ active, onClick, label, icon: Icon }) => (
  <Button variant={active ? "default" : "outline"} size="sm" className="rounded-full gap-1" onClick={onClick} data-testid={`filter-${label.toLowerCase()}`}>
    {Icon && <Icon size={16} weight={active ? "fill" : "regular"} />} {label}
  </Button>
);
