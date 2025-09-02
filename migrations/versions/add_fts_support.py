"""Add full-text search support

Revision ID: add_fts_support
Revises: 
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'add_fts_support'
down_revision = None
depends_on = None


def upgrade():
    """Add full-text search support"""
    # Get database connection
    conn = op.get_bind()
    
    # Check if we're using SQLite
    if 'sqlite' in str(conn.engine.url):
        # Create FTS5 virtual table for inventory items
        conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS inventory_fts USING fts5(
                id UNINDEXED,
                title,
                authors,
                description,
                content='inventory_item',
                content_rowid='id'
            )
        """))
        
        # Populate FTS table with existing data
        conn.execute(text("""
            INSERT INTO inventory_fts(id, title, authors, description)
            SELECT id, title, authors, description FROM inventory_item
        """))
        
        # Create triggers to keep FTS table in sync
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS inventory_fts_insert AFTER INSERT ON inventory_item BEGIN
                INSERT INTO inventory_fts(id, title, authors, description)
                VALUES (new.id, new.title, new.authors, new.description);
            END
        """))
        
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS inventory_fts_delete AFTER DELETE ON inventory_item BEGIN
                DELETE FROM inventory_fts WHERE id = old.id;
            END
        """))
        
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS inventory_fts_update AFTER UPDATE ON inventory_item BEGIN
                DELETE FROM inventory_fts WHERE id = old.id;
                INSERT INTO inventory_fts(id, title, authors, description)
                VALUES (new.id, new.title, new.authors, new.description);
            END
        """))
        
        # Create FTS5 virtual table for donors
        conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS donor_fts USING fts5(
                id UNINDEXED,
                name,
                email,
                notes,
                content='donor',
                content_rowid='id'
            )
        """))
        
        # Populate donor FTS table
        conn.execute(text("""
            INSERT INTO donor_fts(id, name, email, notes)
            SELECT id, name, email, notes FROM donor
        """))
        
        # Create triggers for donor FTS
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS donor_fts_insert AFTER INSERT ON donor BEGIN
                INSERT INTO donor_fts(id, name, email, notes)
                VALUES (new.id, new.name, new.email, new.notes);
            END
        """))
        
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS donor_fts_delete AFTER DELETE ON donor BEGIN
                DELETE FROM donor_fts WHERE id = old.id;
            END
        """))
        
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS donor_fts_update AFTER UPDATE ON donor BEGIN
                DELETE FROM donor_fts WHERE id = old.id;
                INSERT INTO donor_fts(id, name, email, notes)
                VALUES (new.id, new.name, new.email, new.notes);
            END
        """))
    
    elif 'postgresql' in str(conn.engine.url):
        # For PostgreSQL, create GIN indexes for full-text search
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_inventory_fts_title 
            ON inventory_item USING gin(to_tsvector('english', title))
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_inventory_fts_authors 
            ON inventory_item USING gin(to_tsvector('english', authors))
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_inventory_fts_description 
            ON inventory_item USING gin(to_tsvector('english', description))
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_donor_fts_name 
            ON donor USING gin(to_tsvector('english', name))
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_donor_fts_notes 
            ON donor USING gin(to_tsvector('english', notes))
        """))


def downgrade():
    """Remove full-text search support"""
    conn = op.get_bind()
    
    if 'sqlite' in str(conn.engine.url):
        # Drop triggers
        conn.execute(text("DROP TRIGGER IF EXISTS inventory_fts_insert"))
        conn.execute(text("DROP TRIGGER IF EXISTS inventory_fts_delete"))
        conn.execute(text("DROP TRIGGER IF EXISTS inventory_fts_update"))
        conn.execute(text("DROP TRIGGER IF EXISTS donor_fts_insert"))
        conn.execute(text("DROP TRIGGER IF EXISTS donor_fts_delete"))
        conn.execute(text("DROP TRIGGER IF EXISTS donor_fts_update"))
        
        # Drop FTS tables
        conn.execute(text("DROP TABLE IF EXISTS inventory_fts"))
        conn.execute(text("DROP TABLE IF EXISTS donor_fts"))
    
    elif 'postgresql' in str(conn.engine.url):
        # Drop GIN indexes
        conn.execute(text("DROP INDEX IF EXISTS idx_inventory_fts_title"))
        conn.execute(text("DROP INDEX IF EXISTS idx_inventory_fts_authors"))
        conn.execute(text("DROP INDEX IF EXISTS idx_inventory_fts_description"))
        conn.execute(text("DROP INDEX IF EXISTS idx_donor_fts_name"))
        conn.execute(text("DROP INDEX IF EXISTS idx_donor_fts_notes"))