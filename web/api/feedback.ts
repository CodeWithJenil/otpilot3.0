import { VercelRequest, VercelResponse } from '@vercel/node';
import { neon } from '@neondatabase/serverless';
import { z } from 'zod';

interface FeedbackSubmission {
  feedback_type: string;
  rating?: number;
  feedback: string;
  email?: string;
  otpilot_version?: string;
  operating_system?: string;
  python_version?: string;
}

// Neon SQL connection - uses DATABASE_URL environment variable
const sql = neon(process.env.DATABASE_URL!);

// Validation schema matching the frontend
const feedbackSchema = z.object({
  feedback_type: z.enum(['bug', 'feature_request', 'improvement', 'general']),
  rating: z.number().int().min(1).max(5).optional(),
  feedback: z.string().min(10).max(5000),
  email: z.string().email().max(254).optional(),
  otpilot_version: z.string().max(50).optional(),
  operating_system: z.string().max(100).optional(),
  python_version: z.string().max(50).optional(),
});

function validateFeedback(body: unknown): body is FeedbackSubmission {
  const result = feedbackSchema.safeParse(body);
  return result.success;
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

  // Validate payload size (max 10KB for feedback)
  const contentLength = req.headers['content-length'];
  if (contentLength && parseInt(contentLength, 10) > 10240) {
    return res.status(413).json({ error: 'Payload too large' });
  }

  // Check database connection
  if (!process.env.DATABASE_URL) {
    console.error('DATABASE_URL environment variable not set');
    return res.status(500).json({ error: 'Database not configured' });
  }

  try {
    const body = req.body as FeedbackSubmission;

    if (!validateFeedback(body)) {
      return res.status(400).json({ error: 'Invalid feedback payload' });
    }

    // Insert into Neon database
    await sql`
      INSERT INTO feedback_submissions (
        feedback_type,
        rating,
        feedback,
        email,
        otpilot_version,
        operating_system,
        python_version
      ) VALUES (
        ${body.feedback_type},
        ${body.rating ?? null},
        ${body.feedback},
        ${body.email ?? null},
        ${body.otpilot_version ?? null},
        ${body.operating_system ?? null},
        ${body.python_version ?? null}
      )
    `;

    // Log for debugging (without sensitive data)
    console.log(`Feedback: ${body.feedback_type} received`);

    return res.status(202).json({ accepted: true });
  } catch (error) {
    console.error('Feedback error:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
}