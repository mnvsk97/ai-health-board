"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { TranscriptEntry } from "@/lib/types";

interface TranscriptViewerProps {
  transcript: TranscriptEntry[];
  autoScroll?: boolean;
}

export function TranscriptViewer({
  transcript,
  autoScroll = true,
}: TranscriptViewerProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [transcript, autoScroll]);

  if (transcript.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        <p>Waiting for conversation to start...</p>
      </div>
    );
  }

  return (
    <ScrollArea className="h-[500px] pr-4" ref={scrollRef}>
      <div className="space-y-4">
        {transcript.map((entry, index) => (
          <TranscriptMessage key={index} entry={entry} />
        ))}
      </div>
    </ScrollArea>
  );
}

function TranscriptMessage({ entry }: { entry: TranscriptEntry }) {
  const isSystem = entry.role === "system";
  const isTester = entry.role === "tester";

  if (isSystem) {
    return (
      <div className="flex justify-center">
        <span className="text-xs text-muted-foreground bg-muted px-3 py-1 rounded-full">
          {entry.content}
        </span>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-col",
        isTester ? "items-end" : "items-start"
      )}
    >
      <div
        className={cn(
          "max-w-[80%] rounded-lg p-3",
          isTester
            ? "bg-blue-50 dark:bg-blue-950 text-blue-900 dark:text-blue-100"
            : "bg-muted text-foreground"
        )}
      >
        <p className="text-xs font-medium mb-1 opacity-70">
          {isTester ? "Pen Tester" : "Target Agent"}
        </p>
        <p className="text-sm whitespace-pre-wrap">{entry.content}</p>
      </div>
      <span className="text-xs text-muted-foreground mt-1 px-1">
        {formatTime(entry.timestamp)}
      </span>
    </div>
  );
}

function formatTime(timestamp: number): string {
  const date = new Date(timestamp * 1000);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
