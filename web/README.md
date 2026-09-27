# OTPilot Web Official Site

Official website and documentation frontend for the [OTPilot](https://pypi.org/project/otpilot/) PyPI package.

## Features

- Package overview and product principles
- PyPI release & installation guide
- Terminal animation demo
- Privacy & Terms documentation
- **Telemetry API** - Optional anonymous usage analytics (opt-in)

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

### 3) Environment Variables (Vercel Dashboard)

Add the following environment variable in Vercel Project Settings → Environment Variables:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Neon PostgreSQL connection string (e.g., `postgresql://user:pass@host/db?sslmode=require`) |

## Telemetry API

OTPilot 3.0 includes an optional, opt-in telemetry system. The web backend provides two endpoints:

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/telemetry` | POST | Accept telemetry events from OTPilot CLI |
| `/api/telemetry-query` | GET | Query stored telemetry events (admin/debug) |

### Database Setup (Neon)

The telemetry data is stored in a single PostgreSQL table `telemetry_events`.

#### 1. Create a Neon Database
1. Go to [neon.tech](https://neon.tech) and create a project
2. Copy the connection string (looks like `postgresql://user:pass@host/db?sslmode=require`)

#### 2. Run Schema Migration
```bash
cd web
export DATABASE_URL="your-neon-connection-string"
npm run db:setup
```

This creates the `telemetry_events` table with indexes and constraints.

#### 3. Set DATABASE_URL in Vercel
Add the same connection string as an environment variable in your Vercel project settings.

### Local Testing

You can test the full telemetry pipeline locally:

#### Terminal 1: Start local telemetry server
```bash
cd /path/to/otpilot3.0
export DATABASE_URL="your-neon-connection-string"
python3 local_telemetry_server.py
```

#### Terminal 2: Run OTPilot with local endpoint
```bash
export OTPILOT_TELEMETRY_ENDPOINT=http://localhost:8080/api/telemetry
otpilot telemetry enable
otpilot version
otpilot telemetry disable
```

The local server will print received events in real-time and store them in your Neon database.

### Querying Telemetry Data

```bash
# Query recent events
curl "https://your-vercel-app.vercel.app/api/telemetry-query?limit=50"

# Filter by event type
curl "https://your-vercel-app.vercel.app/api/telemetry-query?event=command_executed"

# Filter by installation ID
curl "https://your-vercel-app.vercel.app/api/telemetry-query?installation_id=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

# Filter by command
curl "https://your-vercel-app.vercel.app/api/telemetry-query?command=fetch"
```

### Schema

The `telemetry_events` table:

```sql
CREATE TABLE telemetry_events (
    id BIGSERIAL PRIMARY KEY,
    installation_id UUID NOT NULL,
    event VARCHAR(50) NOT NULL,
    version VARCHAR(20) NOT NULL,
    python_version VARCHAR(10) NOT NULL,
    os VARCHAR(20) NOT NULL,
    architecture VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    command VARCHAR(50),
    extra JSONB,
    received_at TIMESTAMPTZ DEFAULT NOW()
);
```

Indexes on: `installation_id`, `event`, `received_at`, `command`.

Check constraints ensure only allowed events and commands are stored.

## Architecture & Privacy

OTPilot 3.0 is local-first. Email retrieval uses IMAP over SSL with provider App Passwords stored directly in the user's operating system credential vault (macOS Keychain / Windows Credential Manager / Linux Secret Service).

The web frontend is a zero-dependency static documentation site and does not require Firebase, cloud servers, or external auth relays.

**Telemetry is opt-in only** - users must explicitly run `otpilot telemetry enable` to activate it. See [PRIVACY.md](../PRIVACY.md) for full details.