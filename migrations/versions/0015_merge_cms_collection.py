"""Merge CMS reviews and collection recovery without rewriting either history."""

revision = "0015_merge_cms_collection"
down_revision = ("0013_dossier_area_reviews", "0014_collection_attempts")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
