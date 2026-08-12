import {
  Bell,
  Bot,
  Briefcase,
  Building2,
  CalendarDays,
  CircleDollarSign,
  FileStack,
  FileText,
  FolderKanban,
  Home,
  LayoutDashboard,
  MessageSquare,
  ScrollText,
  Settings,
  Shield,
  Users,
  UserRound,
  Workflow,
  Puzzle,
  BookTemplate,
  ClipboardList,
  KeyRound,
  type LucideIcon,
} from "lucide-react";

export type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  /** If set, item only shows when `can(perm)` is true (founder `*` counts). */
  perm?: string;
};

export const primaryNav: NavItem[] = [
  { href: "/home", label: "Home", icon: Home },
  { href: "/desk", label: "My Desk", icon: LayoutDashboard },
  { href: "/projects", label: "Projects", icon: FolderKanban },
  { href: "/clients", label: "Clients", icon: Building2, perm: "clients:read" },
  { href: "/tasks", label: "Tasks", icon: ClipboardList },
  { href: "/docs", label: "Docs", icon: FileText, perm: "files:read" },
  { href: "/team", label: "Team", icon: Users, perm: "employees:read" },
  { href: "/leads", label: "Leads", icon: Briefcase, perm: "leads:read" },
  { href: "/calendar", label: "Calendar", icon: CalendarDays },
  { href: "/messages", label: "Messages", icon: MessageSquare, perm: "messages:read" },
  { href: "/files", label: "Files", icon: FileStack, perm: "files:read" },
  { href: "/vault", label: "Vault", icon: KeyRound, perm: "credentials:read" },
  { href: "/finance", label: "Finance", icon: CircleDollarSign, perm: "finance:read" },
  { href: "/reports", label: "Reports", icon: ScrollText, perm: "reports:read" },
  { href: "/ai", label: "Sunny AI", icon: Bot, perm: "ai:use" },
  { href: "/notifications", label: "Notifications", icon: Bell },
];

export const adminNav: NavItem[] = [
  { href: "/admin/employees", label: "Employees", icon: UserRound },
  { href: "/admin/departments", label: "Departments", icon: Workflow },
  { href: "/admin/permissions", label: "Permissions", icon: Shield },
  { href: "/admin/integrations", label: "Integrations", icon: Puzzle },
  { href: "/admin/templates", label: "Templates", icon: BookTemplate },
  { href: "/admin/settings", label: "Company Settings", icon: Settings },
  { href: "/admin/audit", label: "Audit Logs", icon: ScrollText, perm: "audit:read" },
];
