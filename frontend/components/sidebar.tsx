"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FlaskConical,
  Shield,
  Plus,
  FileText,
  Crosshair,
  Layers,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";

const navItems = [
  {
    label: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    label: "Test Runs",
    href: "/runs",
    icon: FlaskConical,
  },
  {
    label: "Batch Runs",
    href: "/batches",
    icon: Layers,
  },
  {
    label: "Scenarios",
    href: "/scenarios",
    icon: FileText,
  },
  {
    label: "Attack Vectors",
    href: "/attacks",
    icon: Crosshair,
  },
  {
    label: "Compliance",
    href: "/compliance",
    icon: Shield,
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="flex h-full flex-col bg-background">
      {/* Logo */}
      <div className="px-4 py-5 border-b">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Shield className="h-5 w-5" />
          </div>
          <span className="font-semibold tracking-tight">AI Health Board</span>
        </Link>
      </div>

      {/* Primary Action */}
      <div className="p-4">
        <Button asChild className="w-full">
          <Link href="/new">
            <Plus className="mr-2 h-4 w-4" />
            New Test
          </Link>
        </Button>
      </div>

      {/* Navigation */}
      <ScrollArea className="flex-1 px-2">
        <p className="px-2 py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Navigation
        </p>
        <nav className="space-y-1">
          {navItems.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.href !== "/" && pathname.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-secondary text-secondary-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </ScrollArea>

      {/* Footer */}
      <Separator />
      <div className="p-4">
        <p className="text-xs text-muted-foreground text-center">
          AI Health Board v0.1
        </p>
      </div>
    </div>
  );
}
