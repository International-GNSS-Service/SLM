from django.db import migrations

# TODO when migrations are squashed - we need to reinclude this one


class Migration(migrations.Migration):
    dependencies = [
        # Replace with your latest migration
        ("slm", "0032_archiveindex_valid_range_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS idx_archiveindex_lower_bound
                ON slm_archiveindex (lower(valid_range));
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS idx_archiveindex_lower_bound;
            """,
        ),
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS idx_archiveindex_upper_bound
                ON slm_archiveindex (upper(valid_range));
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS idx_archiveindex_upper_bound;
            """,
        ),
        # for idempotency - drop it first
        migrations.RunSQL(
            """
            ALTER TABLE slm_archiveindex
            DROP CONSTRAINT IF EXISTS index_valid_range_lower_not_null;
            """,
            reverse_sql="""
            ALTER TABLE slm_archiveindex
            ADD CONSTRAINT index_valid_range_lower_not_null
            CHECK (lower(valid_range) IS NOT NULL);
            """,
        ),
        migrations.RunSQL(
            """
            ALTER TABLE slm_archiveindex
            ADD CONSTRAINT index_valid_range_lower_not_null
            CHECK (lower(valid_range) IS NOT NULL);
            """,
            reverse_sql="""
            ALTER TABLE slm_archiveindex
            DROP CONSTRAINT IF EXISTS index_valid_range_lower_not_null;
            """,
        ),
    ]
