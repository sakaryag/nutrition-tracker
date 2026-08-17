#!/usr/bin/env python3
"""
SQLite to Neon Postgres Migration Script

Migrates all data from a local SQLite file to Neon Postgres in dependency order.

Usage:
    python scripts/migrate_to_postgres.py

Environment Variables:
    SQLITE_URL      SQLite connection string (default: sqlite:///nutritrack.db)
    POSTGRES_URL    Postgres connection string (required). Example:
                    postgresql://user:pass@host/db?sslmode=require

The script is idempotent: it checks if data already exists in Postgres before
migrating each table. If rows already exist, that table is skipped.
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect, MetaData
from sqlalchemy.pool import NullPool

# Table migration order based on foreign key dependencies
MIGRATION_TIERS = [
    # Tier 1: No FK dependencies
    ['user', 'saved_food', 'nutrition_plan'],
    
    # Tier 2: FK to Tier 1 only
    ['daily_target', 'meal_template', 'water_log', 'daily_note', 
     'friend_connection', 'feed_visibility', 'user_badge', 'plan_task',
     'user_plan_assignment'],
    
    # Tier 3: FK to Tier 1-2
    ['food_entry', 'meal_template_item', 'plan_task_completion'],
    
    # Tier 4: FK to Tier 1-3
    ['shared_entry'],
    
    # Note: dietitian_access and dietitian_visit are created via raw SQL in app.py
    # If data exists in SQLite, add migration here
]

BATCH_SIZE = 500


def get_row_count(engine, table_name):
    """Count rows in a table using the given engine."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
            return result.scalar()
    except Exception:
        return 0


def migrate_table(sqlite_engine, postgres_engine, table_name, use_batching=False):
    """Migrate a single table from SQLite to Postgres.
    
    Args:
        sqlite_engine: SQLAlchemy engine for SQLite
        postgres_engine: SQLAlchemy engine for Postgres
        table_name: Name of table to migrate
        use_batching: If True, migrate in batches of BATCH_SIZE rows
    
    Returns:
        (rows_migrated, rows_skipped) tuple
    """
    # Check if data already exists in Postgres
    pg_count = get_row_count(postgres_engine, table_name)
    if pg_count > 0:
        print(f'  {table_name}: {pg_count} rows already exist (skipping)')
        return 0, pg_count
    
    # Get row count in SQLite
    sqlite_count = get_row_count(sqlite_engine, table_name)
    if sqlite_count == 0:
        print(f'  {table_name}: 0 rows (nothing to migrate)')
        return 0, 0
    
    try:
        # Get table metadata from SQLite
        metadata = MetaData()
        metadata.reflect(bind=sqlite_engine, only=[table_name])
        table = metadata.tables[table_name]
        
        if use_batching and sqlite_count > BATCH_SIZE:
            print(f'Migrating {table_name}: {sqlite_count} rows...', end='', flush=True)
            migrated = 0
            offset = 0
            
            while offset < sqlite_count:
                # Read batch from SQLite
                with sqlite_engine.connect() as conn:
                    batch_sql = text(f'SELECT * FROM "{table_name}" LIMIT {BATCH_SIZE} OFFSET {offset}')
                    rows = conn.execute(batch_sql).fetchall()
                
                if not rows:
                    break
                
                # Insert batch into Postgres
                with postgres_engine.connect() as conn:
                    if rows:
                        insert_sql = table.insert()
                        conn.execute(insert_sql, [dict(row._mapping) for row in rows])
                        conn.commit()
                
                migrated += len(rows)
                offset += BATCH_SIZE
                print('.', end='', flush=True)
            
            print(' done')
            return migrated, 0
        else:
            # Non-batched migration (for small tables)
            print(f'Migrating {table_name}: {sqlite_count} rows...', end='', flush=True)
            
            with sqlite_engine.connect() as conn:
                rows = conn.execute(text(f'SELECT * FROM "{table_name}"')).fetchall()
            
            if rows:
                with postgres_engine.connect() as conn:
                    insert_sql = table.insert()
                    conn.execute(insert_sql, [dict(row._mapping) for row in rows])
                    conn.commit()
            
            print(' done')
            return sqlite_count, 0
    
    except Exception as e:
        print(f' ERROR: {e}')
        return 0, 0


def reset_sequences(postgres_engine):
    """Reset all SERIAL sequences in Postgres to prevent PK conflicts."""
    print('\nResetting sequences...')
    
    try:
        with postgres_engine.connect() as conn:
            # Query all tables with SERIAL primary keys
            result = conn.execute(text("""
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE is_identity = 'YES' OR column_default LIKE 'nextval%'
            """))
            
            for table_name, column_name in result:
                seq_name = f"{table_name}_{column_name}_seq"
                max_sql = text(f'SELECT MAX({column_name}) FROM "{table_name}"')
                max_result = conn.execute(max_sql)
                max_val = max_result.scalar() or 0
                
                setval_sql = text(f"SELECT setval('{seq_name}', {max_val} + 1, FALSE)")
                try:
                    conn.execute(setval_sql)
                    conn.commit()
                    print(f'  {seq_name} -> {max_val + 1}')
                except Exception as e:
                    print(f'  {seq_name}: skipped ({e})')
    except Exception as e:
        print(f'Warning: Could not reset sequences: {e}')


def verify_migration(postgres_engine):
    """Print final row counts in Postgres."""
    print('\nVerification - Row counts in Postgres:')
    print('-' * 50)
    
    tables_to_check = [
        'user', 'saved_food', 'nutrition_plan',
        'daily_target', 'meal_template', 'water_log', 'daily_note',
        'friend_connection', 'feed_visibility', 'user_badge', 'plan_task',
        'user_plan_assignment', 'food_entry', 'meal_template_item',
        'plan_task_completion', 'shared_entry'
    ]
    
    total_rows = 0
    for table_name in tables_to_check:
        count = get_row_count(postgres_engine, table_name)
        print(f'{table_name:30} {count:8} rows')
        total_rows += count
    
    print('-' * 50)
    print(f'Total rows migrated: {total_rows}')


def main():
    """Main migration function."""
    # Get connection strings from environment
    sqlite_url = os.getenv('SQLITE_URL', 'sqlite:///nutritrack.db')
    postgres_url = os.getenv('POSTGRES_URL')
    
    if not postgres_url:
        print('ERROR: POSTGRES_URL environment variable is required')
        print('Example: POSTGRES_URL=postgresql://user:pass@host/db?sslmode=require')
        sys.exit(1)
    
    print('SQLite to Postgres Migration')
    print('=' * 60)
    print(f'SQLite:   {sqlite_url}')
    print(f'Postgres: {postgres_url}')
    print('=' * 60)
    
    # Create engines
    try:
        sqlite_engine = create_engine(sqlite_url, poolclass=NullPool)
        postgres_engine = create_engine(postgres_url, poolclass=NullPool)
        
        # Test connections
        with sqlite_engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        print('✓ Connected to SQLite')
        
        with postgres_engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        print('✓ Connected to Postgres')
    except Exception as e:
        print(f'ERROR: Could not connect to databases: {e}')
        sys.exit(1)
    
    print()
    
    # Create all tables in Postgres using db.create_all() equivalent
    # Since we can't use Flask here, we'll ensure tables exist via metadata reflection
    print('Creating tables in Postgres...')
    try:
        metadata = MetaData()
        metadata.reflect(bind=sqlite_engine)
        metadata.create_all(postgres_engine)
        print('✓ Tables created/verified')
    except Exception as e:
        print(f'Warning: Table creation issue: {e}')
    
    print()
    
    # Migrate tables in tiers
    total_migrated = 0
    total_skipped = 0
    
    for tier_num, tier_tables in enumerate(MIGRATION_TIERS, 1):
        print(f'Tier {tier_num} - Migrating {len(tier_tables)} table(s)...')
        
        for table_name in tier_tables:
            # Use batching for large tables
            use_batch = table_name == 'saved_food'
            migrated, skipped = migrate_table(
                sqlite_engine, postgres_engine, table_name, use_batching=use_batch
            )
            total_migrated += migrated
            total_skipped += skipped
        
        print()
    
    print(f'Migration Summary:')
    print(f'  Rows migrated: {total_migrated}')
    print(f'  Rows skipped:  {total_skipped}')
    print()
    
    # Reset sequences
    reset_sequences(postgres_engine)
    
    # Verify migration
    verify_migration(postgres_engine)
    
    print()
    print('Migration complete!')
    print('Next steps:')
    print('  1. Test the deployed application')
    print('  2. Monitor connection pool and storage on Neon dashboard')
    print('  3. (Optional) Run seed_meals() to fill meal entries')


if __name__ == '__main__':
    main()