import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from airwar.core_bindings import (
    spatial_hash_collide,
    spatial_hash_collide_single,
    RUST_AVAILABLE,
)

pytestmark = pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust core not available")


class TestCollisionBindings:
    """Test spatial hash collision detection bindings."""

    def test_spatial_hash_collide_overlapping(self):
        """Two entities that overlap should collide."""
        entities = [
            (1, 0.0, 0.0, 10.0),
            (2, 5.0, 5.0, 10.0),
        ]
        collisions = spatial_hash_collide(entities, 100)
        assert len(collisions) == 1
        assert 1 in collisions[0]
        assert 2 in collisions[0]

    def test_spatial_hash_collide_non_overlapping(self):
        """Two entities far apart should not collide."""
        entities = [
            (1, 0.0, 0.0, 10.0),
            (2, 200.0, 200.0, 10.0),
        ]
        collisions = spatial_hash_collide(entities, 100)
        assert len(collisions) == 0

    def test_spatial_hash_collide_three_entities(self):
        """Three entities - two collide, one doesn't."""
        entities = [
            (1, 0.0, 0.0, 10.0),
            (2, 5.0, 5.0, 10.0),   # Collides with 1
            (3, 100.0, 100.0, 10.0),  # Does not collide with 1 or 2
        ]
        collisions = spatial_hash_collide(entities, 100)
        # Should have exactly one collision pair
        assert len(collisions) == 1
        assert (1, 2) in collisions or (2, 1) in collisions

    def test_spatial_hash_collide_different_cells(self):
        """Entities in different grid cells far apart."""
        entities = [
            (1, 50.0, 50.0, 10.0),
            (2, 450.0, 450.0, 10.0),
        ]
        collisions = spatial_hash_collide(entities, 100)
        assert len(collisions) == 0

    def test_spatial_hash_collide_boundary(self):
        """Entities exactly on boundary of collision."""
        # Two entities with half_size 10, centers 20 apart - just touching
        entities = [
            (1, 0.0, 0.0, 10.0),
            (2, 19.9, 0.0, 10.0),  # Should collide (overlap 0.1)
        ]
        collisions = spatial_hash_collide(entities, 100)
        assert len(collisions) == 1

    def test_spatial_hash_collide_large_entity_count(self):
        """Test with many entities to ensure performance."""
        import random
        random.seed(42)

        entities = []
        for i in range(100):
            x = random.uniform(0, 500)
            y = random.uniform(0, 500)
            half = random.uniform(5, 20)
            entities.append((i, x, y, half))

        collisions = spatial_hash_collide(entities, 100)
        # Just ensure it completes without error
        assert isinstance(collisions, list)

    def test_spatial_hash_collide_single_hit(self):
        """Test spatial_hash_collide_single with target hitting one entity."""
        entities = [
            (1, 0.0, 0.0, 10.0),
            (2, 5.0, 5.0, 10.0),
            (3, 100.0, 100.0, 10.0),
        ]
        hits = spatial_hash_collide_single(entities, 5.0, 5.0, 10.0, 100)
        assert len(hits) == 2
        assert 1 in hits
        assert 2 in hits
        assert 3 not in hits

    def test_spatial_hash_collide_single_no_hit(self):
        """Test spatial_hash_collide_single with no collisions."""
        entities = [
            (1, 0.0, 0.0, 10.0),
            (2, 200.0, 200.0, 10.0),
        ]
        hits = spatial_hash_collide_single(entities, 100.0, 100.0, 10.0, 100)
        assert len(hits) == 0

    def test_spatial_hash_collide_single_boundary(self):
        """Test spatial_hash_collide_single on boundary."""
        entities = [(1, 0.0, 0.0, 10.0)]
        hits = spatial_hash_collide_single(entities, 19.9, 0.0, 10.0, 100)
        assert 1 in hits

        hits = spatial_hash_collide_single(entities, 20.1, 0.0, 10.0, 100)
        assert 1 not in hits

    def test_spatial_hash_collide_empty(self):
        """Test with empty entity list."""
        collisions = spatial_hash_collide([], 100)
        assert collisions == []

    def test_spatial_hash_collide_single_empty(self):
        """Test spatial_hash_collide_single with empty entity list."""
        hits = spatial_hash_collide_single([], 0.0, 0.0, 10.0, 100)
        assert hits == []

    def test_spatial_hash_collide_idempotent(self):
        """Running collision check twice should give same results."""
        entities = [
            (1, 0.0, 0.0, 10.0),
            (2, 5.0, 5.0, 10.0),
            (3, 100.0, 100.0, 10.0),
        ]
        collisions1 = spatial_hash_collide(entities, 100)
        collisions2 = spatial_hash_collide(entities, 100)
        assert sorted(collisions1) == sorted(collisions2)