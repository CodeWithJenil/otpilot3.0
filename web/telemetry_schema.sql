-- Telemetry table for Neon PostgreSQL
-- Run this in your Neon SQL editor or via migration tool

CREATE TABLE IF NOT EXISTS telemetry_events (
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

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_telemetry_installation_id ON telemetry_events(installation_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_event ON telemetry_events(event);
CREATE INDEX IF NOT EXISTS idx_telemetry_received_at ON telemetry_events(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_command ON telemetry_events(command);

-- Optional: Add a check constraint for event types
ALTER TABLE telemetry_events
ADD CONSTRAINT chk_telemetry_event CHECK (event IN (
    'app_started',
    'command_executed',
    'telemetry_enabled',
    'telemetry_disabled'
));

-- Optional: Add a check constraint for commands
ALTER TABLE telemetry_events
ADD CONSTRAINT chk_telemetry_command CHECK (
    command IS NULL OR command IN (
        'fetch', 'watch', 'hotkey', 'login', 'logout',
        'config', 'doctor', 'version', 'telemetry'
    )
);