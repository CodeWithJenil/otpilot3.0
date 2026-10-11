-- Feedback table for Neon PostgreSQL
-- Run this in your Neon SQL editor or via migration tool

CREATE TABLE IF NOT EXISTS feedback_submissions (
    id BIGSERIAL PRIMARY KEY,
    feedback_type TEXT NOT NULL,
    rating INTEGER,
    feedback TEXT NOT NULL,
    email TEXT,
    otpilot_version TEXT,
    operating_system TEXT,
    python_version TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT feedback_type_check
        CHECK (
            feedback_type IN (
                'bug',
                'feature_request',
                'improvement',
                'general'
            )
        ),

    CONSTRAINT rating_check
        CHECK (
            rating IS NULL OR rating BETWEEN 1 AND 5
        )
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON feedback_submissions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback_submissions(feedback_type);
CREATE INDEX IF NOT EXISTS idx_feedback_version ON feedback_submissions(otpilot_version);

-- Optional: Add a check constraint for email format (basic validation at DB level)
-- ALTER TABLE feedback_submissions
-- ADD CONSTRAINT chk_feedback_email CHECK (
--     email IS NULL OR email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
-- );