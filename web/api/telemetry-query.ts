import { VercelRequest, VercelResponse } from '@vercel/node';
import { neon } from '@neondatabase/serverless';

const sql = neon(process.env.DATABASE_URL!);

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  if (!process.env.DATABASE_URL) {
    return res.status(500).json({ error: 'Database not configured' });
  }

  try {
    // Query parameters
    const limit = Math.min(parseInt(req.query.limit as string) || 100, 1000);
    const offset = parseInt(req.query.offset as string) || 0;
    const event = req.query.event as string;
    const installationId = req.query.installation_id as string;
    const command = req.query.command as string;
    const since = req.query.since as string;

    // Build query dynamically
    let whereClause = '';
    const params: (string | number)[] = [];
    let paramIndex = 1;

    const conditions: string[] = [];

    if (event) {
      conditions.push(`event = $${paramIndex++}`);
      params.push(event);
    }
    if (installationId) {
      conditions.push(`installation_id = $${paramIndex++}::uuid`);
      params.push(installationId);
    }
    if (command) {
      conditions.push(`command = $${paramIndex++}`);
      params.push(command);
    }
    if (since) {
      conditions.push(`received_at >= $${paramIndex++}::timestamptz`);
      params.push(since);
    }

    if (conditions.length > 0) {
      whereClause = 'WHERE ' + conditions.join(' AND ');
    }

    // Add limit and offset
    params.push(limit, offset);

    const query = `
      SELECT
        id,
        installation_id,
        event,
        version,
        python_version,
        os,
        architecture,
        timestamp,
        command,
        extra,
        received_at
      FROM telemetry_events
      ${whereClause}
      ORDER BY received_at DESC
      LIMIT $${paramIndex++} OFFSET $${paramIndex}
    `;

    const rows = await sql.query(query, params);

    // Get total count
    const countQuery = `
      SELECT COUNT(*) as total
      FROM telemetry_events
      ${whereClause}
    `;
    const countResult = await sql.query(countQuery, params.slice(0, -2));
    const total = parseInt(countResult[0]?.total as string) || 0;

    return res.status(200).json({
      events: rows,
      pagination: {
        limit,
        offset,
        total,
        hasMore: offset + limit < total,
      },
    });
  } catch (error) {
    console.error('Telemetry query error:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
}