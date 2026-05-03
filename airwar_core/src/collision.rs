use pyo3::prelude::*;
use std::collections::HashMap;

/// Spatial hash grid for efficient collision detection
/// Entities are stored in grid cells based on their position
#[derive(Debug, Clone)]
pub struct SpatialHashGrid {
    cell_size: i32,
    cells: HashMap<i64, Vec<i32>>,
    entity_positions: HashMap<i32, (f32, f32, f32)>, // id -> (x, y, half_size)
}

impl SpatialHashGrid {
    pub fn new(cell_size: i32) -> Self {
        Self {
            cell_size,
            cells: HashMap::new(),
            entity_positions: HashMap::new(),
        }
    }

    pub fn clear(&mut self) {
        self.cells.clear();
        self.entity_positions.clear();
    }

    fn pos_to_key(x: i32, y: i32) -> i64 {
        ((x as i64) << 32) | (y as i64 & 0xFFFFFFFF)
    }

    pub fn insert(&mut self, id: i32, x: f32, y: f32, half_size: f32) {
        let half_s = half_size;

        let min_x = (x - half_s) as i32 / self.cell_size;
        let max_x = (x + half_s) as i32 / self.cell_size;
        let min_y = (y - half_s) as i32 / self.cell_size;
        let max_y = (y + half_s) as i32 / self.cell_size;

        for gx in min_x..=max_x {
            for gy in min_y..=max_y {
                let key = Self::pos_to_key(gx, gy);
                self.cells.entry(key).or_default().push(id);
            }
        }

        self.entity_positions.insert(id, (x, y, half_size));
    }

    pub fn get_potential_collisions(&self, x: f32, y: f32, half_size: f32) -> Vec<i32> {
        let min_x = (x - half_size) as i32 / self.cell_size;
        let max_x = (x + half_size) as i32 / self.cell_size;
        let min_y = (y - half_size) as i32 / self.cell_size;
        let max_y = (y + half_size) as i32 / self.cell_size;

        let mut seen = std::collections::HashSet::new();
        let mut result = Vec::new();

        for gx in min_x..=max_x {
            for gy in min_y..=max_y {
                let key = Self::pos_to_key(gx, gy);
                if let Some(ids) = self.cells.get(&key) {
                    for &id in ids {
                        if seen.insert(id) {
                            result.push(id);
                        }
                    }
                }
            }
        }

        result
    }

    pub fn get_position(&self, id: i32) -> Option<(f32, f32, f32)> {
        self.entity_positions.get(&id).copied()
    }
}

/// Axis-Aligned Bounding Box
#[derive(Debug, Clone, Copy)]
pub struct AABB {
    pub min_x: f32,
    pub min_y: f32,
    pub max_x: f32,
    pub max_y: f32,
}

impl AABB {
    pub fn from_xy_half_size(x: f32, y: f32, half_size: f32) -> Self {
        Self {
            min_x: x - half_size,
            min_y: y - half_size,
            max_x: x + half_size,
            max_y: y + half_size,
        }
    }

    pub fn intersects(&self, other: &AABB) -> bool {
        self.min_x < other.max_x
            && self.max_x > other.min_x
            && self.min_y < other.max_y
            && self.max_y > other.min_y
    }
}

/// SIMD-enabled collision check using SSE2
/// Falls back to scalar if SIMD is not available
#[cfg(target_feature = "sse2")]
#[target_feature(enable = "sse2")]
unsafe fn simd_collide_rects_sse(a: &AABB, b: &AABB) -> bool {
    use std::arch::x86_64::*;

    // Load AABB values
    let a_min = _mm_loadu_ps([a.min_x, a.min_y, a.max_x, a.max_y].as_ptr());
    let b_max = _mm_loadu_ps([b.max_x, b.max_y, b.min_x, b.min_y].as_ptr());
    let a_max = _mm_loadu_ps([a.max_x, a.max_y, a.min_x, a.min_y].as_ptr());
    let b_min = _mm_loadu_ps([b.min_x, b.min_y, b.max_x, b.max_y].as_ptr());

    let cmp_min = _mm_cmplt_ps(a_min, b_max); // a.min < b.max
    let cmp_max = _mm_cmpgt_ps(a_max, b_min); // a.max > b.min

    // Combine: (a.min < b.max) & (a.max > b.min)
    let result = _mm_and_ps(cmp_min, cmp_max);

    // Check if both x and y pass (lower two floats)
    let mask = _mm_movemask_ps(result);
    mask & 0b0011 == 0b0011
}

#[cfg(not(target_feature = "sse2"))]
unsafe fn simd_collide_rects_sse(_a: &AABB, _b: &AABB) -> bool {
    // Fallback to scalar
    _a.intersects(_b)
}

pub fn check_collision(a: &AABB, b: &AABB) -> bool {
    // Use SIMD if available, otherwise scalar
    unsafe { simd_collide_rects_sse(a, b) }
}

/// Check collision between two entities described by position and half_size
pub fn check_entity_collision(
    ax: f32,
    ay: f32,
    a_half: f32,
    bx: f32,
    by: f32,
    b_half: f32,
) -> bool {
    let a = AABB::from_xy_half_size(ax, ay, a_half);
    let b = AABB::from_xy_half_size(bx, by, b_half);
    check_collision(&a, &b)
}

/// Persistent spatial hash for incremental collision detection
/// Avoids rebuilding the grid every frame
#[pyclass]
pub struct PersistentSpatialHash {
    inner: SpatialHashGrid,
}

#[pymethods]
impl PersistentSpatialHash {
    #[new]
    pub fn new(cell_size: i32) -> Self {
        Self {
            inner: SpatialHashGrid::new(cell_size),
        }
    }

    /// Clear all entities from the hash
    pub fn clear(&mut self) {
        self.inner.clear();
    }

    /// Insert or update an entity's position
    pub fn update_entity(&mut self, id: i32, x: f32, y: f32, half_size: f32) {
        // Remove from old cells first if entity exists
        if let Some((old_x, old_y, old_half)) = self.inner.entity_positions.get(&id).copied() {
            Self::remove_from_cells(&mut self.inner, id, old_x, old_y, old_half);
        }
        // Insert at new position
        self.inner.insert(id, x, y, half_size);
    }

    /// Batch update multiple entities
    pub fn update_entities(&mut self, entities: Vec<(i32, f32, f32, f32)>) {
        for (id, x, y, half_size) in entities {
            self.update_entity(id, x, y, half_size);
        }
    }

    /// Remove an entity from the hash
    pub fn remove_entity(&mut self, id: i32) {
        if let Some((x, y, half_size)) = self.inner.entity_positions.get(&id).copied() {
            Self::remove_from_cells(&mut self.inner, id, x, y, half_size);
            self.inner.entity_positions.remove(&id);
        }
    }

    /// Get all collision pairs among entities in the hash
    pub fn get_collisions(&self) -> Vec<(i32, i32)> {
        let mut collision_pairs = Vec::new();
        let mut checked = std::collections::HashSet::new();

        for (&id, &(x, y, half_size)) in &self.inner.entity_positions {
            let potential = self.inner.get_potential_collisions(x, y, half_size);

            for &other_id in &potential {
                if other_id == id {
                    continue;
                }

                let (smaller, larger) = if id < other_id {
                    (id, other_id)
                } else {
                    (other_id, id)
                };
                let pair_key = ((smaller as i64) << 32) | (larger as i64);

                if checked.contains(&pair_key) {
                    continue;
                }
                checked.insert(pair_key);

                if let (Some((ox, oy, o_half)), Some((_, _, _))) = (
                    self.inner.get_position(other_id),
                    self.inner.get_position(id),
                ) {
                    if check_entity_collision(x, y, half_size, ox, oy, o_half) {
                        collision_pairs.push((id, other_id));
                    }
                }
            }
        }

        collision_pairs
    }

    /// Query entities that might collide with a given position
    pub fn query(&self, x: f32, y: f32, half_size: f32) -> Vec<i32> {
        self.inner.get_potential_collisions(x, y, half_size)
    }
}

impl PersistentSpatialHash {
    fn remove_from_cells(grid: &mut SpatialHashGrid, id: i32, x: f32, y: f32, half_size: f32) {
        let min_x = (x - half_size) as i32 / grid.cell_size;
        let max_x = (x + half_size) as i32 / grid.cell_size;
        let min_y = (y - half_size) as i32 / grid.cell_size;
        let max_y = (y + half_size) as i32 / grid.cell_size;

        for gx in min_x..=max_x {
            for gy in min_y..=max_y {
                let key = SpatialHashGrid::pos_to_key(gx, gy);
                if let Some(cell) = grid.cells.get_mut(&key) {
                    cell.retain(|&e| e != id);
                }
            }
        }
    }
}

/// Batch collision check: player bullets vs enemies.
/// Returns (bullet_id, enemy_id) pairs for every bullet-enemy collision.
///
/// bullets: Vec<(i64 bullet_id, f32 cx, f32 cy, f32 half_size)>
/// enemies: Vec<(i32 enemy_id, f32 cx, f32 cy, f32 half_size)>
#[pyfunction]
pub fn batch_collide_bullets_vs_entities(
    bullets: Vec<(i64, f32, f32, f32)>,
    enemies: Vec<(i32, f32, f32, f32)>,
    cell_size: i32,
) -> Vec<(i64, i32)> {
    if bullets.is_empty() || enemies.is_empty() {
        return Vec::new();
    }

    let mut grid = SpatialHashGrid::new(cell_size);
    for (id, x, y, half_size) in &enemies {
        grid.insert(*id, *x, *y, *half_size);
    }

    let mut results = Vec::new();
    for (bid, bx, by, bhalf) in &bullets {
        let potential = grid.get_potential_collisions(*bx, *by, *bhalf);
        for &eid in &potential {
            if let Some((ex, ey, ehalf)) = grid.get_position(eid) {
                if check_entity_collision(*bx, *by, *bhalf, ex, ey, ehalf) {
                    results.push((*bid, eid));
                }
            }
        }
    }
    results
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_spatial_hash_insert_and_query() {
        let mut grid = SpatialHashGrid::new(100);

        // Two entities in same cell
        grid.insert(1, 50.0, 50.0, 10.0);
        grid.insert(2, 80.0, 80.0, 10.0);

        let potential = grid.get_potential_collisions(50.0, 50.0, 10.0);
        assert!(potential.contains(&1));
        assert!(potential.contains(&2));
    }

    #[test]
    fn test_spatial_hash_separate_cells() {
        let mut grid = SpatialHashGrid::new(100);

        // Two entities in different cells (200 apart)
        grid.insert(1, 50.0, 50.0, 10.0);
        grid.insert(2, 250.0, 250.0, 10.0);

        let potential = grid.get_potential_collisions(50.0, 50.0, 10.0);
        assert!(potential.contains(&1));
        // Entity 2 is not in any cell that overlaps with entity 1's cell
    }

    #[test]
    fn test_aabb_intersection() {
        let a = AABB::from_xy_half_size(0.0, 0.0, 10.0);
        let b = AABB::from_xy_half_size(5.0, 5.0, 10.0);
        assert!(a.intersects(&b));

        let c = AABB::from_xy_half_size(100.0, 100.0, 10.0);
        assert!(!a.intersects(&c));
    }

    #[test]
    fn test_entity_collision() {
        // Overlapping entities
        assert!(check_entity_collision(0.0, 0.0, 10.0, 5.0, 5.0, 10.0));
        // Non-overlapping entities
        assert!(!check_entity_collision(0.0, 0.0, 10.0, 100.0, 100.0, 10.0));
    }

    #[test]
    fn test_batch_collide_bullets_vs_entities() {
        let bullets = vec![(1i64, 0.0, 0.0, 5.0), (2i64, 100.0, 100.0, 5.0)];
        let enemies = vec![(1i32, 0.0, 0.0, 10.0), (2i32, 100.0, 100.0, 10.0)];
        let hits = batch_collide_bullets_vs_entities(bullets, enemies, 50);
        assert_eq!(hits.len(), 2);
    }
}
