import Footer from "@/components/Footer";
import GrainOverlay from "@/components/GrainOverlay";
import LogoMark from "@/components/LogoMark";
import CustomCursor from "@/components/CustomCursor";
import { Link, useParams } from "react-router-dom";

const Installation = () => {
  const { version } = useParams();
  const normalizedVersion = (version?.trim() || "3.0.0").toLowerCase();

  return (
    <main className="min-h-screen bg-background text-foreground">
      <CustomCursor />
      <GrainOverlay />

      <section className="border-b border-border">
        <div className="container mx-auto px-6 py-10 md:py-14 flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <LogoMark compact />
          <div className="flex items-center gap-4">
            <a
              href="https://pypi.org/project/otpilot/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs font-mono text-primary hover:underline border border-primary/30 rounded px-2.5 py-1 bg-primary/10"
            >
              PyPI Package ↗
            </a>
            <p className="font-mono text-sm text-muted-foreground">
              Version: <span className="text-primary">{normalizedVersion}</span>
            </p>
          </div>
        </div>
      </section>

      <section className="container mx-auto px-6 py-10 md:py-14 space-y-12">
        {/* Step 1: Install */}
        <div className="rounded-xl border border-border bg-card/70 p-6 md:p-8 space-y-6">
          <div className="space-y-2">
            <h1 className="text-3xl font-bold">Step 1 — Install via pip</h1>
            <p className="text-muted-foreground">
              OTPilot is published on PyPI. Make sure you have Python 3.12+ installed.
            </p>
          </div>
          
          <pre className="rounded-md border border-border bg-background/40 p-4 font-mono text-sm text-foreground whitespace-pre-wrap leading-relaxed overflow-x-auto">
            pip install otpilot
          </pre>
          
          <div className="flex flex-wrap gap-2 text-xs font-mono text-muted-foreground">
            <span className="px-2 py-1 border border-border rounded">macOS</span>
            <span className="px-2 py-1 border border-border rounded">Windows</span>
            <span className="px-2 py-1 border border-border rounded">Linux (X11)</span>
          </div>
        </div>

        {/* Step 2: App Password */}
        <div className="rounded-xl border border-border bg-card/70 p-6 md:p-8 space-y-6">
          <div className="space-y-2">
            <h2 className="text-2xl font-bold">Step 2 — Get Gmail App Password</h2>
            <p className="text-muted-foreground">
              To connect OTPilot over IMAP/SSL securely without OAuth, create a Google App Password.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            <div className="space-y-4">
              <ul className="space-y-3 text-sm text-muted-foreground list-decimal list-inside">
                <li>Enable <strong>2-Step Verification</strong> on your Google Account</li>
                <li>Go to <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">Google Security → App passwords</a></li>
                <li>Generate a new password (name it <strong>OTPilot</strong>)</li>
                <li>Copy the 16-character generated password</li>
              </ul>
            </div>
            <div className="p-4 rounded border border-border bg-background/20">
              <p className="text-xs text-muted-foreground italic leading-relaxed">
                "Why use App Passwords?" <br /><br />
                Version 3.0 uses IMAP over SSL with provider App Passwords stored securely in your OS vault (macOS Keychain / Windows Credential Manager / Linux Secret Service). No external servers, no telemetry, no third-party OAuth apps.
              </p>
            </div>
          </div>
        </div>

        {/* Step 3: Login */}
        <div className="rounded-xl border border-border bg-card/70 p-6 md:p-8 space-y-6">
          <div className="space-y-2">
            <h2 className="text-2xl font-bold">Step 3 — Login</h2>
            <p className="text-muted-foreground">
              Store your credentials securely in your operating system credential manager.
            </p>
          </div>

          <pre className="rounded-md border border-border bg-background/40 p-4 font-mono text-sm text-foreground">
            otpilot login user@gmail.com
          </pre>

          <p className="text-sm text-muted-foreground">
            When prompted, enter the 16-character <code className="text-primary">Gmail App Password</code> you created in Step 2.
          </p>
        </div>

        {/* Step 4: Launch */}
        <div className="rounded-xl border border-border bg-card/70 p-6 md:p-8 space-y-6">
          <div className="space-y-2">
            <h2 className="text-2xl font-bold">Step 4 — Launch & Use</h2>
            <p className="text-muted-foreground">
              Start the background hotkey listener or run a single fetch.
            </p>
          </div>

          <pre className="rounded-md border border-border bg-background/40 p-4 font-mono text-sm text-foreground">
            otpilot hotkey
          </pre>

          <p className="text-sm text-muted-foreground">
            Press <kbd className="px-1.5 py-0.5 rounded bg-muted text-foreground border border-border">Ctrl+Shift+O</kbd> (or <kbd className="px-1.5 py-0.5 rounded bg-muted text-foreground border border-border">Cmd+Shift+O</kbd> on macOS) to fetch and copy your latest OTP directly to your clipboard.
          </p>
        </div>

        <div className="flex justify-center pt-8">
          <Link
            to="/"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-md bg-zinc-900 text-white font-mono text-sm hover:bg-zinc-800 transition-colors"
          >
            Back to homepage
          </Link>
        </div>
      </section>

      <Footer />
    </main>
  );
};

export default Installation;
