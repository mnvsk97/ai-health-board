"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Play, Loader2, Layers } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Label } from "@/components/ui/label";
import { ScenarioSelector } from "@/components/scenario-selector";
import { createRun, createBatchRun } from "@/lib/api";
import { addRunId } from "@/lib/runs-store";
import type { RunMode } from "@/lib/types";

export default function NewTestPage() {
  const router = useRouter();
  const [agentType, setAgentType] = useState<"intake" | "refill">("intake");
  const [mode, setMode] = useState<RunMode>("text_text");
  const [selectedScenarios, setSelectedScenarios] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Batch mode state
  const [batchMode, setBatchMode] = useState(false);
  const [concurrency, setConcurrency] = useState(10);
  const [turns, setTurns] = useState(3);
  const [maxScenarios, setMaxScenarios] = useState(10);

  const handleSubmit = async () => {
    if (selectedScenarios.length === 0 && !batchMode) {
      setError("Please select at least one scenario");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      if (batchMode) {
        // Create batch run
        const response = await createBatchRun({
          scenario_ids: selectedScenarios.length > 0 ? selectedScenarios : undefined,
          agent_type: agentType,
          concurrency,
          turns,
          max_scenarios: maxScenarios,
        });
        router.push(`/batches/${response.batch_id}`);
      } else {
        // Create single run
        const response = await createRun({
          scenario_ids: selectedScenarios,
          mode,
          agent_type: agentType,
        });
        addRunId(response.run_id);
        router.push(`/runs/${response.run_id}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create test run");
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-10 flex items-center gap-4 border-b bg-background px-8 py-6">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">New Test Run</h1>
          <p className="text-sm text-muted-foreground">
            Configure and launch an adversarial test against your AI agent
          </p>
        </div>
      </header>

      {/* Content */}
      <div className="px-8 py-6 max-w-4xl">
        <div className="grid gap-6 md:grid-cols-2">
          {/* Left Column - Configuration */}
          <div className="space-y-6">
            {/* Agent Type */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Target Agent</CardTitle>
                <CardDescription>
                  Select the type of healthcare AI agent to test
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Select
                  value={agentType}
                  onValueChange={(value: "intake" | "refill") => setAgentType(value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select agent type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="intake">
                      <div className="flex flex-col items-start">
                        <span>Intake Agent</span>
                        <span className="text-xs text-muted-foreground">
                          Patient intake and triage
                        </span>
                      </div>
                    </SelectItem>
                    <SelectItem value="refill">
                      <div className="flex flex-col items-start">
                        <span>Refill Agent</span>
                        <span className="text-xs text-muted-foreground">
                          Prescription refill requests
                        </span>
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </CardContent>
            </Card>

            {/* Batch Mode Toggle */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Layers className="h-5 w-5" />
                  Batch Testing
                </CardTitle>
                <CardDescription>
                  Run multiple scenarios in parallel
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between">
                  <Label htmlFor="batch-mode" className="flex flex-col gap-1">
                    <span>Enable Batch Mode</span>
                    <span className="font-normal text-xs text-muted-foreground">
                      Test all selected scenarios simultaneously
                    </span>
                  </Label>
                  <Switch
                    id="batch-mode"
                    checked={batchMode}
                    onCheckedChange={setBatchMode}
                  />
                </div>

                {batchMode && (
                  <>
                    <div className="space-y-3">
                      <Label className="flex justify-between">
                        <span>Concurrency</span>
                        <span className="text-muted-foreground">{concurrency} parallel</span>
                      </Label>
                      <Slider
                        value={[concurrency]}
                        onValueChange={(v) => setConcurrency(v[0])}
                        min={1}
                        max={20}
                        step={1}
                      />
                      <p className="text-xs text-muted-foreground">
                        Higher values run more scenarios at once but use more resources
                      </p>
                    </div>

                    <div className="space-y-3">
                      <Label className="flex justify-between">
                        <span>Turns per Scenario</span>
                        <span className="text-muted-foreground">{turns} turns</span>
                      </Label>
                      <Slider
                        value={[turns]}
                        onValueChange={(v) => setTurns(v[0])}
                        min={1}
                        max={10}
                        step={1}
                      />
                    </div>

                    <div className="space-y-3">
                      <Label className="flex justify-between">
                        <span>Max Scenarios</span>
                        <span className="text-muted-foreground">{maxScenarios} scenarios</span>
                      </Label>
                      <Slider
                        value={[maxScenarios]}
                        onValueChange={(v) => setMaxScenarios(v[0])}
                        min={1}
                        max={50}
                        step={1}
                      />
                      <p className="text-xs text-muted-foreground">
                        Limit the number of scenarios to run in this batch
                      </p>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

            {/* Test Mode */}
            {!batchMode && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Test Mode</CardTitle>
                  <CardDescription>
                    Choose how the tester interacts with the target agent
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Tabs value={mode} onValueChange={(v) => setMode(v as RunMode)}>
                    <TabsList className="grid w-full grid-cols-3">
                      <TabsTrigger value="text_text">Text</TabsTrigger>
                      <TabsTrigger value="text_voice">Text→Voice</TabsTrigger>
                      <TabsTrigger value="voice_voice">Voice</TabsTrigger>
                    </TabsList>
                    <TabsContent value="text_text" className="mt-4">
                      <p className="text-sm text-muted-foreground">
                        Both tester and target communicate via text. Fastest mode for
                        rapid iteration.
                      </p>
                    </TabsContent>
                    <TabsContent value="text_voice" className="mt-4">
                      <p className="text-sm text-muted-foreground">
                        Tester sends text, target responds with voice. Tests voice
                        synthesis quality.
                      </p>
                    </TabsContent>
                    <TabsContent value="voice_voice" className="mt-4">
                      <p className="text-sm text-muted-foreground">
                        Full voice-to-voice conversation. Most realistic but slower
                        execution.
                      </p>
                    </TabsContent>
                  </Tabs>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right Column - Scenarios */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Test Scenarios</CardTitle>
              <CardDescription>
                Select the scenarios to run against the target agent
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ScenarioSelector
                selectedIds={selectedScenarios}
                onChange={setSelectedScenarios}
              />
            </CardContent>
          </Card>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mt-6 p-4 bg-destructive/10 text-destructive rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Submit Button */}
        <div className="mt-6 flex items-center justify-end gap-4">
          <Button variant="outline" asChild>
            <Link href="/">Cancel</Link>
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || (!batchMode && selectedScenarios.length === 0)}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Starting...
              </>
            ) : batchMode ? (
              <>
                <Layers className="mr-2 h-4 w-4" />
                Start Batch Testing
                {selectedScenarios.length > 0
                  ? ` (${selectedScenarios.length} selected)`
                  : " (all approved)"}
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Start Test ({selectedScenarios.length} scenario
                {selectedScenarios.length !== 1 ? "s" : ""})
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
