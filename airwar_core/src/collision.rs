use pyo3::prelude::*;
use std::collections::HashMap;

/// Spatial hash grid for efficient collision detection
/// Entities are stored in grid cells based on their position
#[derive(Debug, Clone)]
pub struct SpatialHashGrid {
    cell_size: i32,
    cells: HashMap<i64, Vec<i64>>,
    entity_positions: HashMap<i64, AABB>,
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
        (i64::from(x) << 32) | (i64::from(y) & 0xFFFF_FFFF)
    }

    pub fn insert(&mut self, id: i64, x: f32, y: f32, width: f32, height: f32) {
        let bounds = AABB::from_xy_size(x, y, width, height);
        self.insert_aabb(id, bounds);
    }

    fn insert_aabb(&mut self, id: i64, bounds: AABB) {
        let min_x = (bounds.min_x / self.cell_size as f32).floor() as i32;
        let max_x = (bounds.max_x / self.cell_size as f32).floor() as i32;
        let min_y = (bounds.min_y / self.cell_size as f32).floor() as i32;
        let max_y = (bounds.max_y / self.cell_size as f32).floor() as i32;

        for gx in min_x..=max_x {
            for gy in min_y..=max_y {
                let key = Self::pos_to_key(gx, gy);
                self.cells.entry(key).or_default().push(id);
            }
        }

        self.entity_positions.insert(id, bounds);
    }

    pub fn get_potential_collisions(&self, x: f32, y: f32, width: f32, height: f32) -> Vec<i64> {
        let bounds = AABB::from_xy_size(x, y, width, height);
        self.get_potential_collisions_for_aabb(bounds)
    }

    fn get_potential_collisions_for_aabb(&self, bounds: AABB) -> Vec<i64> {
        let min_x = (bounds.min_x / self.cell_size as f32).floor() as i32;
        let max_x = (bounds.max_x / self.cell_size as f32).floor() as i32;
        let min_y = (bounds.min_y / self.cell_size as f32).floor() as i32;
        let max_y = (bounds.max_y / self.cell_size as f32).floor() as i32;

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

    pub fn get_position(&self, id: i64) -> Option<AABB> {
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
    pub fn from_xy_size(x: f32, y: f32, width: f32, height: f32) -> Self {
        Self {
            min_x: x,
            min_y: y,
            max_x: x + width,
            max_y: y + height,
        }
    }

    pub fn from_xy_half_size(x: f32, y: f32, half_size: f32) -> Self {
        Self {
            min_x: x - half_size,
            min_y: y - half_size,
            max_x: x + half_size,
            max_y: y + half_size,
        }
    }

    pub fn intersects(&self, other: &AABB) -> bool {
        self.min_x < other.max_x && self.max_x > other.min_x && self.min_y < other.max_y && self.max_y > other.min_y
    }
}

/// SIMD-enabled collision check using SSE2
/// Falls back to scalar if SIMD is not available
#[cfg(target_feature = "sse2")]
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
unsafe fn simd_collide_rects_sse(a: &AABB, b: &AABB) -> bool {
    // Fallback to scalar
    a.intersects(b)
}

pub fn check_collision(a: &AABB, b: &AABB) -> bool {
    // Use SIMD if available, otherwise scalar
    // SAFETY: simd_collide_rects_sse only reads four f32 fields from valid
    // AABB references and falls back to scalar on targets without SSE2.
    unsafe { simd_collide_rects_sse(a, b) }
}

/// Check collision between two entities described by position and `half_size`
pub fn check_entity_collision(ax: f32, ay: f32, a_half: f32, bx: f32, by: f32, b_half: f32) -> bool {
    let a = AABB::from_xy_half_size(ax, ay, a_half);
    let b = AABB::from_xy_half_size(bx, by, b_half);
    check_collision(&a, &b)
}

/// Batch collision check: player bullets vs enemies.
/// Returns (`bullet_id`, `enemy_id`) pairs for every bullet-enemy collision.
///
/// bullets: Vec<(i64 `bullet_id`, f32 x, f32 y, f32 width, f32 height)>
/// enemies: Vec<(i64 `enemy_id`, f32 x, f32 y, f32 width, f32 height)>
#[pyfunction]
pub fn batch_collide_bullets_vs_entities(
    bullets: Vec<(i64, f32, f32, f32, f32)>,
    enemies: Vec<(i64, f32, f32, f32, f32)>,
    cell_size: i32,
) -> Vec<(i64, i64)> {
    if bullets.is_empty() || enemies.is_empty() || cell_size <= 0 {
        return Vec::new();
    }

    let mut grid = SpatialHashGrid::new(cell_size);
    for (id, x, y, width, height) in &enemies {
        grid.insert(*id, *x, *y, *width, *height);
    }

    let mut results = Vec::new();
    for (bid, bx, by, bwidth, bheight) in &bullets {
        let bullet_bounds = AABB::from_xy_size(*bx, *by, *bwidth, *bheight);
        let potential = grid.get_potential_collisions_for_aabb(bullet_bounds);
        for &eid in &potential {
            if let Some(enemy_bounds) = grid.get_position(eid) {
                if check_collision(&bullet_bounds, &enemy_bounds) {
                    results.push((*bid, eid));
                }
            }
        }
    }
    results
}
