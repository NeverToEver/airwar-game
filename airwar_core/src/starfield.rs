use pyo3::prelude::*;

/// Per-star input: (x_frac, y_frac, size, brightness, twinkle_speed, twinkle_offset).
/// All fractions are 0.0-1.0 (relative to screen dimensions).
/// `twinkle_speed`/`twinkle_offset` are radians/sec and radians — combined
/// with `time` they index into `sin_table`.
type StarInput = (f32, f32, f32, f32, f32, f32);

/// Per-star output: (x, y, core_brightness, size_int, has_glow, glow_alpha).
/// `x`/`y` are absolute screen pixels. `has_glow=True` means the caller
/// should also blit the cached glow surface at the same position.
type StarOutput = (i32, i32, i32, i32, bool, i32);

/// Compute per-star render positions and brightness in a single Rust call.
///
/// Replaces the per-frame Python loop in `StarLayer.render` (210 iterations
/// with dict lookups, sin-table lookups, and conditional checks). The Python
/// side passes the same sin table it uses for the fallback path so visual
/// output is byte-identical regardless of which path runs.
///
/// Args:
///     stars: List of `(x_frac, y_frac, size, brightness, twinkle_speed, twinkle_offset)`.
///     scroll_offset: Layer scroll (added to `y_frac` before modulo 1.0).
///     screen_w: Screen width in pixels.
///     screen_h: Screen height in pixels.
///     time: Game time in seconds.
///     sin_table: Pre-computed sine table (size must be power of 2).
///     sin_table_size: Size of `sin_table` (also power of 2).
///     sin_table_mask: `sin_table_size - 1` (mask for fast modulo).
///     glow_threshold: Brightness above which a glow ring is drawn.
///     glow_alpha_divisor: `brightness / divisor` becomes glow alpha.
///     glow_alpha_cap: Max glow alpha.
///
/// Returns:
///     List of `(x, y, core_brightness, size_int, has_glow, glow_alpha)`.
#[pyfunction]
#[pyo3(signature = (stars, scroll_offset, screen_w, screen_h, time, sin_table, sin_table_size, sin_table_mask, glow_threshold, glow_alpha_divisor, glow_alpha_cap))]
pub fn compute_starfield_positions(
    stars: Vec<StarInput>,
    scroll_offset: f32,
    screen_w: f32,
    screen_h: f32,
    time: f32,
    sin_table: Vec<f32>,
    sin_table_size: usize,
    sin_table_mask: usize,
    glow_threshold: i32,
    glow_alpha_divisor: i32,
    glow_alpha_cap: i32,
) -> Vec<StarOutput> {
    if sin_table.is_empty() || glow_alpha_divisor == 0 {
        return Vec::new();
    }
    let _ = sin_table_mask;
    let scale = sin_table_size as f32 / std::f32::consts::TAU;
    let mut out = Vec::with_capacity(stars.len());

    for star in &stars {
        let (x_frac, y_frac, size, brightness, twinkle_speed, twinkle_offset) = *star;

        // y wraps via (y_frac + scroll) mod 1.0 — `rem_euclid` matches Python's `% 1.0` for positive results.
        let y_norm = (y_frac + scroll_offset).rem_euclid(1.0);
        let x = (x_frac * screen_w) as i32;
        let y_pos = (y_norm * screen_h) as i32;

        // Sin-table twinkle lookup (matches `twinkle_phase = (time * speed + offset) * (size / TAU)`).
        let phase = (time * twinkle_speed + twinkle_offset) * scale;
        let idx = (phase as i32).rem_euclid(sin_table.len() as i32) as usize;
        let twinkle = sin_table[idx];

        // Brightness: `brightness * (0.5 + 0.5 * sin) * 255`, clamped to 0..255.
        let b = (brightness * (0.5 + 0.5 * twinkle) * 255.0) as i32;
        let core_b = b.clamp(0, 255);
        let size_int = size.max(1.0) as i32;

        let has_glow = b > glow_threshold;
        let glow_alpha = if has_glow {
            (b / glow_alpha_divisor).min(glow_alpha_cap)
        } else {
            0
        };

        out.push((x, y_pos, core_b, size_int, has_glow, glow_alpha));
    }

    out
}
