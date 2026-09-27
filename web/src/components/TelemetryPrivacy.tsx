import { useEffect, useRef, useState } from "react";
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "@/components/ui/accordion";
import { cn } from "@/lib/utils";

const collectedItems = [
  { label: "OTPilot version", key: "version", example: "3.0.1" },
  { label: "Python version", key: "python_version", example: "3.14" },
  { label: "Operating system", key: "os", example: "macOS" },
  { label: "CPU architecture", key: "architecture", example: "arm64" },
  { label: "Anonymous installation ID", key: "installation_id", example: "a1b2c3d4-..." },
  { label: "Basic event type", key: "event", example: "app_started" },
  { label: "UTC timestamp", key: "timestamp", example: "2026-09-27T10:15:00Z" },
];

const neverCollectedItems = [
  "Email addresses",
  "Email contents",
  "OTP codes",
  "Passwords or credentials",
  "Clipboard contents",
  "File paths",
  "Usernames",
  "Hostnames",
  "Exact location / IP addresses",
  "Command arguments",
  "Personally identifiable information",
];

const cliCommands = [
  "$ otpilot telemetry status",
  "$ otpilot telemetry enable",
  "$ otpilot telemetry disable",
];

const examplePayload = {
  event: "app_started",
  version: "3.0.1",
  python_version: "3.14",
  os: "macOS",
  architecture: "arm64",
  installation_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  timestamp: "2026-09-27T10:15:00Z",
};

const notDerivedFrom = [
  "email address",
  "username",
  "hostname",
  "MAC address",
  "hardware serial number",
];

const TelemetryPrivacy = () => {
  const ref = useRef<HTMLDivElement>(null);
  const [showCursor, setShowCursor] = useState(true);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) entry.target.classList.add("visible");
        });
      },
      { threshold: 0.1 }
    );
    const els = ref.current?.querySelectorAll(".reveal");
    els?.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  // Subtle cursor blink for terminal feel
  useEffect(() => {
    const interval = setInterval(() => setShowCursor((prev) => !prev), 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <section
      ref={ref}
      className="py-24 lg:py-32 border-t border-border"
      aria-labelledby="telemetry-heading"
    >
      <div className="container mx-auto px-6">
        {/* Header */}
        <div className="reveal text-center max-w-3xl mx-auto mb-16">
          <h2 id="telemetry-heading" className="text-3xl md:text-4xl font-bold tracking-tight mb-4">
            Telemetry & Privacy
          </h2>
          <p className="text-lg text-muted-foreground font-body leading-relaxed">
            Anonymous by default. Optional when you want to help improve OTPilot.
          </p>
        </div>

        {/* Main Panel - Terminal Style */}
        <div className="reveal max-w-4xl mx-auto" style={{ transitionDelay: "100ms" }}>
          <div className="rounded-lg border border-border bg-card overflow-hidden shadow-2xl shadow-primary/5">
            {/* Title bar */}
            <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-card/50">
              <div className="w-3 h-3 rounded-full bg-[hsl(0,70%,45%)]" />
              <div className="w-3 h-3 rounded-full bg-[hsl(45,70%,45%)]" />
              <div className="w-3 h-3 rounded-full bg-[hsl(120,50%,40%)]" />
              <span className="ml-2 text-xs text-muted-foreground font-mono">telemetry</span>
              <span className="ml-auto text-xs text-muted-foreground font-mono opacity-50">v3.0</span>
            </div>

            {/* Panel body */}
            <div className="p-4 md:p-6 font-mono text-sm leading-relaxed">
              {/* Intro text */}
              <div className="mb-6 space-y-2 text-muted-foreground font-body text-sm max-w-xl">
                <p>
                  OTPilot can optionally send a small amount of anonymous operational data to help
                  improve compatibility and understand how the project is used.
                </p>
                <p>
                  Telemetry is disabled by default and is never required for OTPilot to work.
                </p>
              </div>

              {/* Status Display */}
              <div className="mb-8">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs text-muted-foreground uppercase tracking-wider">STATUS</span>
                </div>
                <div className="flex items-center gap-4 flex-wrap">
                  <span
                    className={cn(
                      "inline-flex items-center gap-2 px-3 py-1.5 rounded border font-mono text-xs",
                      "bg-secondary text-muted-foreground border-muted-foreground/30"
                    )}
                    role="status"
                    aria-label="Telemetry status: disabled"
                  >
                    <span
                      className="relative flex h-2 w-2 rounded-full bg-muted-foreground"
                      aria-hidden="true"
                    >
                      <span className={cn(
                        "absolute inset-0 rounded-full opacity-30",
                        "bg-primary"
                      )} />
                    </span>
                    <span className="text-xs font-semibold">OFF</span>
                  </span>
                  <span className="text-muted-foreground font-body text-sm">
                    Disabled by default.
                  </span>
                </div>
              </div>

              {/* What is Collected */}
              <div className="mb-8">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs text-primary uppercase tracking-wider">COLLECTED</span>
                  <span className="text-xs text-muted-foreground">
                    {collectedItems.length} fields
                  </span>
                </div>
                <div className="grid sm:grid-cols-2 gap-2 md:gap-3">
                  {collectedItems.map((item) => (
                    <div
                      key={item.key}
                      className={cn(
                        "flex items-center gap-3 px-3 py-2.5 rounded border transition-colors",
                        "bg-secondary/30 border-primary/20 text-foreground"
                      )}
                    >
                      <span
                        className="flex items-center justify-center w-5 h-5 rounded border border-primary text-primary text-[10px] font-bold shrink-0"
                        aria-hidden="true"
                      >
                        ✓
                      </span>
                      <span className="font-mono text-sm">{item.label}</span>
                      <span className="ml-auto text-xs text-muted-foreground opacity-70 font-mono">
                        <span className="text-primary/50">"</span>{item.example}<span className="text-primary/50">"</span>
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* What is Never Collected */}
              <div className="mb-8">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs text-destructive uppercase tracking-wider">NEVER COLLECTED</span>
                  <span className="text-xs text-muted-foreground">
                    {neverCollectedItems.length} items
                  </span>
                </div>
                <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-2">
                  {neverCollectedItems.map((item, i) => (
                    <div
                      key={item}
                      className={cn(
                        "flex items-center gap-2 px-3 py-2 rounded border transition-colors",
                        "bg-secondary/30 border-destructive/20 text-destructive/80"
                      )}
                    >
                      <span
                        className="flex items-center justify-center w-5 h-5 rounded border border-destructive text-destructive text-[10px] font-bold shrink-0"
                        aria-hidden="true"
                      >
                        ✕
                      </span>
                      <span className="font-mono text-sm">{item}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* CLI Commands */}
              <div className="mb-8">
                <span className="text-xs text-muted-foreground uppercase tracking-wider block mb-4">CLI COMMANDS</span>
                <div className="rounded-lg bg-secondary/50 border border-border p-4 font-mono text-sm space-y-2">
                  {cliCommands.map((cmd, i) => (
                    <div
                      key={cmd}
                      className="flex items-center gap-3 group relative overflow-hidden"
                    >
                      <span className="text-primary/60 group-hover:text-primary transition-colors">
                        $
                      </span>
                      <code className="text-foreground font-mono text-sm select-all">{cmd}</code>
                      <span
                        className={cn(
                          "absolute inset-0 bg-primary/10 opacity-0 group-hover:opacity-100 transition-opacity duration-200",
                          i === 1 && "bg-primary/20"
                        )}
                        aria-hidden="true"
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Expandable Payload Section */}
              <Accordion type="single" collapsible className="w-full">
                <AccordionItem value="payload" className="border-t border-border">
                  <AccordionTrigger className={cn(
                    "flex items-center justify-between w-full py-4 font-mono text-sm text-foreground hover:text-primary",
                    "bg-transparent focus:outline-none focus:ring-0"
                  )}>
                    <span className="flex items-center gap-2">
                      <span className="text-xs text-primary uppercase tracking-wider">EXACTLY WHAT GETS SENT</span>
                    </span>
                    <svg className="h-4 w-4 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </AccordionTrigger>
                  <AccordionContent className="pb-6">
                    <div className="space-y-4">
                      {/* Example payload */}
                      <div className="rounded-lg bg-secondary/50 border border-border p-4 overflow-x-auto">
                        <pre className="font-mono text-xs text-foreground leading-relaxed overflow-x-auto whitespace-pre">
{JSON.stringify(examplePayload, null, 2)}
                        </pre>
                      </div>

                      {/* Installation ID note */}
                      <div className="rounded-lg border border-primary/20 bg-primary/5 p-4">
                        <div className="flex items-start gap-3">
                          <span className="flex-shrink-0 w-6 h-6 rounded-full border border-primary/30 flex items-center justify-center text-primary text-[10px] font-bold">
                            i
                          </span>
                          <div className="text-sm text-muted-foreground font-body space-y-2">
                            <p className="font-mono text-primary text-sm">
                              Installation ID is randomly generated (UUID v4)
                            </p>
                            <p>
                              It is <strong className="text-foreground">NOT</strong> derived from:
                            </p>
                            <ul className="list-disc list-inside space-y-1 font-mono text-xs">
                              {notDerivedFrom.map((item, i) => (
                                <li key={i} className="text-muted-foreground/80">
                                  {item}
                                </li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      </div>

                      {/* Privacy language */}
                      <div className="rounded-lg border border-muted-foreground/10 bg-card p-4">
                        <h4 className="font-mono text-xs text-muted-foreground uppercase tracking-wider mb-3">
                          Privacy guarantees
                        </h4>
                        <ul className="space-y-2 text-sm text-muted-foreground font-body">
                          <li className="flex items-start gap-2">
                            <span className="text-primary text-xs mt-0.5">→</span>
                            Telemetry is disabled by default.
                          </li>
                          <li className="flex items-start gap-2">
                            <span className="text-primary text-xs mt-0.5">→</span>
                            When enabled, OTPilot sends a limited set of anonymous operational data.
                          </li>
                          <li className="flex items-start gap-2">
                            <span className="text-primary text-xs mt-0.5">→</span>
                            Telemetry is not required for OTPilot to function.
                          </li>
                          <li className="flex items-start gap-2">
                            <span className="text-primary text-xs mt-0.5">→</span>
                            You can disable telemetry at any time with <code className="font-mono bg-secondary/50 px-1 rounded">otpilot telemetry disable</code>.
                          </li>
                          <li className="flex items-start gap-2">
                            <span className="text-primary text-xs mt-0.5">→</span>
                            Network failures never cause OTPilot commands to fail.
                          </li>
                        </ul>
                      </div>
                    </div>
                  </AccordionContent>
                </AccordionItem>
              </Accordion>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default TelemetryPrivacy;