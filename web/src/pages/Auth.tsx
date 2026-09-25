import { Link } from "react-router-dom";
import LogoMark from "@/components/LogoMark";
import CustomCursor from "@/components/CustomCursor";
import GrainOverlay from "@/components/GrainOverlay";

const Auth = () => {
  return (
    <main className="min-h-screen bg-background text-foreground flex items-center justify-center px-6">
      <CustomCursor />
      <GrainOverlay />
      
      <div className="max-w-md w-full rounded-xl border border-border bg-card/80 p-8 space-y-6 shadow-2xl text-center">
        <div className="flex justify-center mb-2">
          <LogoMark compact />
        </div>
        
        <div className="space-y-2">
          <h1 className="text-2xl font-bold">Local Authentication</h1>
          <p className="text-sm text-muted-foreground leading-relaxed">
            OTPilot 3.0 operates completely local-first. Authentication does not use Firebase or cloud servers.
          </p>
        </div>

        <div className="rounded-lg border border-border bg-background/50 p-4 text-left font-mono text-xs text-muted-foreground space-y-2">
          <p className="text-foreground font-semibold">Quick Setup:</p>
          <p>1. Generate a Gmail App Password</p>
          <p>2. Run in your terminal:</p>
          <p className="text-primary font-bold pt-1">otpilot login user@gmail.com</p>
        </div>

        <p className="text-xs text-muted-foreground">
          Your credentials are saved directly in your operating system credential vault (Keychain / Credential Manager / Secret Service).
        </p>

        <div className="pt-2 flex flex-col gap-3">
          <Link
            to="/installation/latest"
            className="w-full py-2.5 rounded-md bg-primary text-primary-foreground font-mono font-semibold text-sm hover:brightness-110 transition-all"
          >
            View Installation Guide
          </Link>
          <Link
            to="/"
            className="w-full py-2.5 rounded-md border border-border text-muted-foreground font-mono text-xs hover:text-foreground transition-colors"
          >
            Back to Homepage
          </Link>
        </div>
      </div>
    </main>
  );
};

export default Auth;
