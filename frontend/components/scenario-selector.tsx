"use client";

import { useState, useEffect } from "react";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { listScenarios } from "@/lib/api";
import type { Scenario } from "@/lib/types";

interface ScenarioSelectorProps {
  selectedIds: string[];
  onChange: (ids: string[]) => void;
}

export function ScenarioSelector({ selectedIds, onChange }: ScenarioSelectorProps) {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchScenarios = async () => {
      try {
        const data = await listScenarios();
        setScenarios(data.scenarios);
        setError(null);
      } catch (err) {
        console.error("Failed to fetch scenarios:", err);
        setError(err instanceof Error ? err.message : "Failed to load scenarios");
      } finally {
        setLoading(false);
      }
    };
    fetchScenarios();
  }, []);

  const handleToggle = (scenarioId: string) => {
    if (selectedIds.includes(scenarioId)) {
      onChange(selectedIds.filter((id) => id !== scenarioId));
    } else {
      onChange([...selectedIds, scenarioId]);
    }
  };

  const handleSelectAll = () => {
    if (selectedIds.length === scenarios.length) {
      onChange([]);
    } else {
      onChange(scenarios.map((s) => s.scenario_id));
    }
  };

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="animate-pulse">
            <div className="h-20 bg-muted rounded-lg" />
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-center text-muted-foreground">
        <p className="text-destructive">{error}</p>
        <p className="text-sm mt-2">Make sure the backend is running at http://localhost:8000</p>
      </div>
    );
  }

  if (scenarios.length === 0) {
    return (
      <div className="p-4 text-center text-muted-foreground">
        <p>No scenarios available</p>
        <p className="text-sm mt-2">Add scenarios to the backend to get started</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Label className="text-sm text-muted-foreground">
          {selectedIds.length} of {scenarios.length} selected
        </Label>
        <button
          type="button"
          onClick={handleSelectAll}
          className="text-sm text-primary hover:underline"
        >
          {selectedIds.length === scenarios.length ? "Deselect all" : "Select all"}
        </button>
      </div>

      <ScrollArea className="h-[400px] pr-4">
        <div className="space-y-3">
          {scenarios.map((scenario) => (
            <Card
              key={scenario.scenario_id}
              className={`p-4 cursor-pointer transition-colors ${
                selectedIds.includes(scenario.scenario_id)
                  ? "border-primary bg-primary/5"
                  : "hover:bg-muted/50"
              }`}
              onClick={() => handleToggle(scenario.scenario_id)}
            >
              <div className="flex items-start gap-3">
                <Checkbox
                  id={scenario.scenario_id}
                  checked={selectedIds.includes(scenario.scenario_id)}
                  onCheckedChange={() => handleToggle(scenario.scenario_id)}
                  className="mt-1"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Label
                      htmlFor={scenario.scenario_id}
                      className="font-medium cursor-pointer"
                    >
                      {scenario.title}
                    </Label>
                    {scenario.specialty && (
                      <Badge variant="secondary" className="text-xs">
                        {scenario.specialty}
                      </Badge>
                    )}
                    {scenario.state && (
                      <Badge variant="outline" className="text-xs">
                        {scenario.state}
                      </Badge>
                    )}
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
                    {scenario.description}
                  </p>
                  <div className="mt-2 flex gap-1 flex-wrap">
                    {scenario.rubric_criteria.flatMap((c) =>
                      c.tags.map((tag) => (
                        <span
                          key={`${scenario.scenario_id}-${tag}`}
                          className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded"
                        >
                          {tag}
                        </span>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
