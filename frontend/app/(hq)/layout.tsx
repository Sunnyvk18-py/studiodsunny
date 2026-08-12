import { HQShell } from "@/components/shell/hq-shell";

export default function HQLayout({ children }: { children: React.ReactNode }) {
  return <HQShell>{children}</HQShell>;
}
