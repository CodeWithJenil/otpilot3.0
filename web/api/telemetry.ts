import { VercelRequest, VercelResponse } from '@vercel/node';
import { neon } from '@neondatabase/serverless';

interface TelemetryEvent {
  installation_id: string;
  event: string;
  version: string;
  python_version: string;
  os: string;
  architecture: string;
  timestamp: string;
  command?: string;
  extra?: Record<string, unknown>;
}

// Neon SQL connection - uses DATABASE_URL environment variable
const sql = neon(process.env.DATABASE_URL!);

// Allowed events for validation
const ALLOWED_EVENTS = new Set([
  'app_started',
  'command_executed',
  'telemetry_enabled',
  'telemetry_disabled',
]);

// Allowed commands for validation
const ALLOWED_COMMANDS = new Set([
  'fetch',
  'watch',
  'hotkey',
  'login',
  'logout',
  'config',
  'doctor',
  'version',
  'telemetry',
]);

function validateEvent(body: unknown): body is TelemetryEvent {
  if (!body || typeof body !== 'object') return false;
  const event = body as Record<string, unknown>;

  // Required fields
  if (typeof event.installation_id !== 'string') return false;
  if (typeof event.event !== 'string') return false;
  if (typeof event.version !== 'string') return false;
  if (typeof event.python_version !== 'string') return false;
  if (typeof event.os !== 'string') return false;
  if (typeof event.architecture !== 'string') return false;
  if (typeof event.timestamp !== 'string') return false;

  // Validate event type
  if (!ALLOWED_EVENTS.has(event.event)) return false;

  // Validate command if present
  if (event.command !== undefined && typeof event.command === 'string') {
    if (!ALLOWED_COMMANDS.has(event.command)) return false;
  }

  // Validate UUID format for installation_id
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  if (!uuidRegex.test(event.installation_id)) return false;

  return true;
}

export default async function handler(req: VercelRequest, res: VercelResponse) {
  // Only allow POST
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Validate content type
  const contentType = req.headers['content-type'];
  if (!contentType || !contentType.includes('application/json')) {
    return res.status(415).json({ error: 'Content-Type must be application/json' });
  }

  // Validate payload size (max 1KB)
  const contentLength = req.headers['content-length'];
  if (contentLength && parseInt(contentLength, 10) > 1024) {
    return res.status(413).json({ error: 'Payload too large' });
  }

  // Check database connection
  if (!process.env.DATABASE_URL) {
    console.error('DATABASE_URL environment variable not set');
    return res.status(500).json({ error: 'Database not configured' });
  }

  try {
    const body = req.body as TelemetryEvent;

    if (!validateEvent(body)) {
      return res.status(400).json({ error: 'Invalid telemetry payload' });
    }

    // Extract extra fields (anything beyond the known schema)
    const { installation_id, event, version, python_version, os, architecture, timestamp, command, ...extra } = body;

    // Insert into Neon database
    await sql`
      INSERT INTO telemetry_events (
        installation_id,
        event,
        version,
        python_version,
        os,
        architecture,
        timestamp,
        command,
        extra
      ) VALUES (
        ${installation_id}::uuid,
        ${event},
        ${version},
        ${python_version},
        ${os},
        ${architecture},
        ${timestamp}::timestamptz,
        ${command ?? null},
        ${extra && Object.keys(extra).length > 0 ? JSON.stringify(extra) : null}::jsonb
      )
    `;

    // Log for debugging
    console.log(`Telemetry: ${event} from ${installation_id.slice(0, 8)}...`);

    return res.status(202).json({ accepted: true });
  } catch (error) {
    console.error('Telemetry error:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
}