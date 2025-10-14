"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

export default function SpaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const t = useTranslations("sidebar");
  const pathname = usePathname();

  const navItems = [
    { href: "/space/spaces", label: t("spaceList") },
    { href: "/space/sessions", label: t("sessionList") },
    { href: "/space/messages", label: t("messageList") },
    { href: "/space/pages", label: t("pageList") },
  ];

  return (
    <div className="flex h-full">
      {/* Left Navigation */}
      <div className="w-42 border-r bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <nav className="flex flex-col p-2 space-y-1">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "px-3 py-2 text-sm rounded-md transition-colors",
                pathname === item.href
                  ? "bg-accent text-accent-foreground font-medium"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">{children}</div>
    </div>
  );
}

