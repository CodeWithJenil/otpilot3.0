#!/usr/bin/env node
/**
 * Neon Database Setup Script
 * 
 * Run this to create the telemetry table in your Neon database.
 * 
 * Usage:
 *   DATABASE_URL="postgresql://..." npx tsx web/setup_neon.ts
 * 
 * Or add to package.json scripts:
 *   "db:setup": "tsx web/setup_neon.ts"
 */

import { neon } from '@neondatabase/serverless';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function setupDatabase() {
  const databaseUrl = process.env.DATABASE_URL;

  if (!databaseUrl) {
    console.error('❌ DATABASE_URL environment variable not set');
    console.error('   Set it to your Neon connection string:');
    console.error('   export DATABASE_URL="postgresql://user:pass@host/db?sslmode=require"');
    process.exit(1);
  }

  console.log('🔌 Connecting to Neon database...');
  const sql = neon(databaseUrl);

  try {
    // Read schema file
    const schemaPath = join(__dirname, 'telemetry_schema.sql');
    const schema = readFileSync(schemaPath, 'utf-8');

    console.log('📋 Executing schema...');
    
    // Split by semicolon and execute each statement
    const statements = schema
      .split(';')
      .map(s => s.trim())
      .filter(s => s.length > 0 && !s.startsWith('--'));

    for (const stmt of statements) {
      try {
        await sql.unsafe(stmt);
        console.log('  ✓ Executed:', stmt.substring(0, 60).replace('\n', ' ') + '...');
      } catch (err) {
        // Ignore "already exists" errors
        if (err instanceof Error && err.message.includes('already exists')) {
          console.log('  ⏭  Skipped (already exists):', stmt.substring(0, 60).replace('\n', ' ') + '...');
        } else {
          throw err;
        }
      }
    }

    // Verify table exists
    const result = await sql`
      SELECT column_name, data_type 
      FROM information_schema.columns 
      WHERE table_name = 'telemetry_events'
      ORDER BY ordinal_position
    `;

    console.log('\n✅ Table "telemetry_events" created successfully!');
    console.log('\n📊 Columns:');
    for (const col of result) {
      console.log(`   - ${col.column_name}: ${col.data_type}`);
    }

    // Check indexes
    const indexes = await sql`
      SELECT indexname, indexdef
      FROM pg_indexes
      WHERE tablename = 'telemetry_events'
    `;

    console.log('\n🔍 Indexes:');
    for (const idx of indexes) {
      console.log(`   - ${idx.indexname}`);
    }

  } catch (error) {
    console.error('\n❌ Setup failed:', error);
    process.exit(1);
  }
}

setupDatabase();