const { Pool } = require('pg');

const DATABASE_URL = String(process.env.DATABASE_URL || '').trim();

async function main() {
  if (!DATABASE_URL) {
    console.log('[loyalty-rules] DATABASE_URL not set; skipping database rule migration.');
    return;
  }

  const pool = new Pool({
    connectionString: DATABASE_URL,
    ssl: !/localhost|127\.0\.0\.1/.test(DATABASE_URL)
      ? { rejectUnauthorized: false }
      : false
  });

  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    // Match the existing SQLAlchemy StoreSetting schema used by app.py.
    await client.query(`
      CREATE TABLE IF NOT EXISTS store_setting (
        id SERIAL PRIMARY KEY,
        key VARCHAR(50) UNIQUE NOT NULL,
        value TEXT NOT NULL
      )
    `);

    // One-time migration: move the earning rule to ₱60 and record the new
    // redemption minimum. Existing customer point balances are never changed.
    const marker = await client.query(
      'SELECT 1 FROM store_setting WHERE key=$1 LIMIT 1',
      ['loyalty_rule_60_30_v1']
    );

    if (!marker.rowCount) {
      await client.query(
        `INSERT INTO store_setting(key,value)
         VALUES($1,$2)
         ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value`,
        ['loyalty_spend_per_point', '60']
      );
      await client.query(
        `INSERT INTO store_setting(key,value)
         VALUES($1,$2)
         ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value`,
        ['loyalty_min_redemption_points', '30']
      );
      await client.query(
        'INSERT INTO store_setting(key,value) VALUES($1,$2)',
        ['loyalty_rule_60_30_v1', '1']
      );
      console.log('[loyalty-rules] Applied ₱60 = 1 point and 30-point minimum redemption.');
    } else {
      // Keep the setting available even if a partial previous deployment
      // created the marker before one of the rule rows.
      await client.query(
        `INSERT INTO store_setting(key,value)
         VALUES($1,$2)
         ON CONFLICT(key) DO NOTHING`,
        ['loyalty_spend_per_point', '60']
      );
      await client.query(
        `INSERT INTO store_setting(key,value)
         VALUES($1,$2)
         ON CONFLICT(key) DO NOTHING`,
        ['loyalty_min_redemption_points', '30']
      );
      console.log('[loyalty-rules] Rule migration already applied.');
    }

    await client.query('COMMIT');
  } catch (err) {
    await client.query('ROLLBACK').catch(() => {});
    throw err;
  } finally {
    client.release();
    await pool.end();
  }
}

main().catch((err) => {
  console.error('[loyalty-rules] Migration failed:', err);
  process.exit(1);
});
