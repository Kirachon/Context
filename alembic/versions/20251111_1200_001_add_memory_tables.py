"""Add memory system tables

Revision ID: 001
Revises:
Create Date: 2025-11-11 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all memory system tables."""

    # Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('enhanced_prompt', sa.Text(), nullable=True),
        sa.Column('response', sa.Text(), nullable=True),
        sa.Column('intent', sa.String(length=50), nullable=True),
        sa.Column('entities', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('feedback', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('resolution', sa.Boolean(), nullable=True),
        sa.Column('helpful_score', sa.Float(), nullable=True),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('context_sources', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_user_timestamp', 'conversations', ['user_id', 'timestamp'], unique=False)
    op.create_index('idx_intent', 'conversations', ['intent'], unique=False)
    op.create_index('idx_timestamp', 'conversations', ['timestamp'], unique=False)
    op.create_index(op.f('ix_conversations_user_id'), 'conversations', ['user_id'], unique=False)

    # Create code_patterns table
    op.create_table(
        'code_patterns',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('pattern_type', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('example_code', sa.Text(), nullable=True),
        sa.Column('signature', sa.String(length=500), nullable=True),
        sa.Column('language', sa.String(length=50), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('files_using', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('user_preference_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('project_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_pattern_type', 'code_patterns', ['pattern_type'], unique=False)
    op.create_index('idx_project_id', 'code_patterns', ['project_id'], unique=False)
    op.create_index('idx_usage_count', 'code_patterns', ['usage_count'], unique=False)

    # Create solutions table
    op.create_table(
        'solutions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('problem_description', sa.Text(), nullable=False),
        sa.Column('problem_type', sa.String(length=100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('solution_code', sa.Text(), nullable=True),
        sa.Column('solution_description', sa.Text(), nullable=True),
        sa.Column('files_affected', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('success_rate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_resolution_time_sec', sa.Integer(), nullable=True),
        sa.Column('similar_problems', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('cluster_id', sa.String(length=100), nullable=True),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('project_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_success_rate', 'solutions', ['success_rate'], unique=False)
    op.create_index('idx_problem_type', 'solutions', ['problem_type'], unique=False)
    op.create_index('idx_cluster_id', 'solutions', ['cluster_id'], unique=False)
    op.create_index(op.f('ix_solutions_project_id'), 'solutions', ['project_id'], unique=False)

    # Create user_preferences table
    op.create_table(
        'user_preferences',
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('code_style', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Indentation, naming conventions, comment style, etc.'),
        sa.Column('preferred_libraries', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Preferred libraries by category (e.g., testing, http, async)'),
        sa.Column('testing_approach', sa.String(length=50), nullable=True,
                  comment='unit, integration, tdd, bdd, etc.'),
        sa.Column('documentation_level', sa.String(length=50), nullable=True,
                  comment='minimal, moderate, extensive'),
        sa.Column('language_preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Preferences by programming language'),
        sa.Column('project_preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Project-specific preference overrides'),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='0.0',
                  comment='How confident we are in these preferences (0-1)'),
        sa.Column('sample_size', sa.Integer(), nullable=False, server_default='0',
                  comment='Number of commits analyzed'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('user_id')
    )


def downgrade() -> None:
    """Drop all memory system tables."""
    op.drop_table('user_preferences')
    op.drop_table('solutions')
    op.drop_table('code_patterns')
    op.drop_table('conversations')
