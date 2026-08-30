import Link from "next/link";

import {
  PrivacyShieldCheckIcon,
  ToolFileIcon,
} from "@/components/icons/PrivConIcons";
import { AppShell } from "@/components/shell/AppShell";
import { TOOLS } from "@/lib/constants";

export default function Home() {
  return (
    <AppShell currentStep={1}>
      <section className="dashboard-panel" aria-labelledby="dashboard-title">
        <div className="dashboard-intro">
          <h1 id="dashboard-title">Private document tools</h1>
          <p>Choose a conversion tool to begin.</p>
          <div className="dashboard-privacy">
            <PrivacyShieldCheckIcon />
            <span>
              Files are processed entirely on this machine.
              <br />
              Nothing is uploaded anywhere.
            </span>
          </div>
        </div>
        <ul className="dashboard-tools">
          {TOOLS.map((tool) => (
            <li key={tool.id}>
              <Link href={tool.route}>
                <ToolFileIcon name={tool.icon} />
                <span>
                  <strong>{tool.title}</strong>
                  <small>{tool.acceptedFormatLabel}</small>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </AppShell>
  );
}
