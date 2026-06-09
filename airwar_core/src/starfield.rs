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
        let idx = (phase as i32 as usize) & sin_table_mask;
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

#[cfg(test)]
mod tests {
    use super::*;

    fn make_sin_table(size: usize) -> Vec<f32> {
        (0..size)
            .map(|i| (i as f32 / size as f32) * std::f32::consts::TAU)
            .map(|theta| theta.sin())
            .collect()
    }

    #[test]
    fn test_empty_input_returns_empty_output() {
        let sin = make_sin_table(1024);
        let out = compute_starfield_positions(vec![], 0.0, 1920.0, 1080.0, 0.0, sin, 1024, 1023, 200, 8, 60);
        assert!(out.is_empty());
    }

    #[test]
    fn test_single_star_position() {
        let sin = make_sin_table(1024);
        // (x_frac=0.5, y_frac=0.0, size=2.0, brightness=0.8, twinkle_speed=1.0, twinkle_offset=0.0)
        let out = compute_starfield_positions(
            vec![(0.5, 0.0, 2.0, 0.8, 1.0, 0.0)],
            0.0,
            1920.0,
            1080.0,
            0.0, // time=0, twinkle_offset=0 -> phase=0 -> twinkle=sin(0)=0
            sin,
            1024,
            1023,
            200,
            8,
            60,
        );
        assert_eq!(out.len(), 1);
        let (x, y, core_b, size_int, has_glow, glow_alpha) = out[0];
        assert_eq!(x, 960);
        assert_eq!(y, 0);
        assert_eq!(size_int, 2);
        // brightness 0.8 * (0.5 + 0.5 * 0) * 255 = 102
        assert_eq!(core_b, 102);
        assert!(!has_glow); // 102 < 200
        assert_eq!(glow_alpha, 0);
    }

    #[test]
    fn test_scroll_offset_wraps() {
        let sin = make_sin_table(1024);
        // Use exact-f32 inputs (powers of 2 in denominator) so the
        // mod-1.0 + multiply + i32-truncate chain is exact.
        // y_frac=0.5 + scroll=0.75 -> 1.25 -> 0.25 (mod 1.0) -> * 100 = 25.
        // The previous 0.95+0.10 drifts to 0.04999998... mod 1, which
        // truncates to 4 — not what the test wanted to assert.
        let out = compute_starfield_positions(
            vec![(0.0, 0.5, 1.0, 1.0, 0.0, 0.0)],
            0.75,
            100.0,
            100.0,
            0.0,
            sin,
            1024,
            1023,
            200,
            8,
            60,
        );
        let (_, y, _, _, _, _) = out[0];
        assert_eq!(y, 25);
    }

    #[test]
    fn test_glow_above_threshold() {
        let sin = make_sin_table(1024);
        // Use FRAC_PI_2 for twinkle_offset so that phase = (FRAC_PI_2) *
        // (1024/TAU) = 256 exactly, sin_table[256] = sin(0.25 * TAU) =
        // sin(pi/2) = 1.0 exactly, b = 1.0 * (0.5 + 0.5 * 1) * 255 = 255.
        // The previous offset 1.534 used the wrong scale (comment said
        // 166.886; actual 1024/TAU = 162.97) and produced idx=250, sin=0.99915,
        // b=254.89 truncated to 254.
        let out = compute_starfield_positions(
            vec![(0.0, 0.0, 2.0, 1.0, 0.0, std::f32::consts::FRAC_PI_2)],
            0.0,
            100.0,
            100.0,
            0.0,
            sin,
            1024,
            1023,
            200, // glow_threshold
            8,   // glow_alpha_divisor
            60,  // glow_alpha_cap
        );
        let (_, _, core_b, _, has_glow, glow_alpha) = out[0];
        assert_eq!(core_b, 255);
        assert!(has_glow);
        // glow_alpha = 255/8 = 31
        assert!(glow_alpha > 0);
    }
}
