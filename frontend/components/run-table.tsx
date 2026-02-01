"use client";

import Link from "next/link";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { StatusIndicator } from "@/components/status-indicator";
import { Badge } from "@/components/ui/badge";
import type { Run } from "@/lib/types";
import { formatDistanceToNow } from "@/lib/format";

interface RunTableProps {
  runs: Run[];
}

export function RunTable({ runs }: RunTableProps) {
  if (runs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <p>No test runs yet</p>
        <p className="text-sm">Create a new test to get started</p>
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="text-xs uppercase tracking-wide text-muted-foreground">
            Run ID
          </TableHead>
          <TableHead className="text-xs uppercase tracking-wide text-muted-foreground">
            Mode
          </TableHead>
          <TableHead className="text-xs uppercase tracking-wide text-muted-foreground">
            Scenarios
          </TableHead>
          <TableHead className="text-xs uppercase tracking-wide text-muted-foreground">
            Status
          </TableHead>
          <TableHead className="text-xs uppercase tracking-wide text-muted-foreground text-right">
            Started
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {runs.map((run) => (
          <TableRow
            key={run.run_id}
            className="cursor-pointer hover:bg-muted/50"
          >
            <TableCell>
              <Link
                href={`/runs/${run.run_id}`}
                className="font-medium hover:underline"
              >
                {run.run_id}
              </Link>
            </TableCell>
            <TableCell>
              <Badge variant="secondary">
                {run.mode.replace(/_/g, " ")}
              </Badge>
            </TableCell>
            <TableCell>
              <span className="text-muted-foreground">
                {run.scenario_ids.length} scenario
                {run.scenario_ids.length !== 1 ? "s" : ""}
              </span>
            </TableCell>
            <TableCell>
              <StatusIndicator status={run.status} size="sm" />
            </TableCell>
            <TableCell className="text-right text-muted-foreground">
              {run.started_at
                ? formatDistanceToNow(run.started_at)
                : "—"}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
