# OTPilot Web Official Site

Official website and documentation frontend for the [OTPilot](https://pypi.org/project/otpilot/) PyPI package.

## Features

- Package overview and product principles
- PyPI release & installation guide
- Terminal animation demo
- Privacy & Terms documentation

## Build and Deploy (Vercel)

### 1) Build locally

```bash
cd web
npm install
npm run build
```

This produces static assets in `web/dist`.

### 2) Deploy to Vercel

1. Push this repo to GitHub.
2. In Vercel, click **Add New Project** and import the repo.
3. Set **Root Directory** to `web`.
4. Framework preset: **Vite**.
5. Build command: `npm run build`.
6. Output directory: `dist`.

## Architecture & Privacy

OTPilot 3.0 is local-first. Email retrieval uses IMAP over SSL with provider App Passwords stored directly in the user's operating system credential vault (macOS Keychain / Windows Credential Manager / Linux Secret Service).

The web frontend is a zero-dependency static documentation site and does not require Firebase, cloud servers, or external auth relays.
