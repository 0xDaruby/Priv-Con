import "./catalog.css";

import { ToolCatalog } from "@/components/catalog/ToolCatalog";
import { AppShell } from "@/components/shell/AppShell";

export default function Home() {
  return (
    <AppShell variant="catalog">
      <ToolCatalog />
    </AppShell>
  );
}
