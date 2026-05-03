use pyo3::prelude::*;

#[derive(Clone, Copy)]
struct RgbaColor(u8, u8, u8);

/// Fill a circle with alpha gradient (glow effect)
#[allow(clippy::too_many_arguments)]
fn fill_glow_circle(
    data: &mut [u8],
    width: usize,
    height: usize,
    cx: f32,
    cy: f32,
    radius: f32,
    color: RgbaColor,
    glow_radius: f32,
) {
    let mut min_x = (cx - glow_radius - 2.0) as isize;
    let mut max_x = (cx + glow_radius + 2.0) as isize;
    let mut min_y = (cy - glow_radius - 2.0) as isize;
    let mut max_y = (cy + glow_radius + 2.0) as isize;

    if min_x < 0 {
        min_x = 0;
    }
    if max_x > width as isize {
        max_x = width as isize;
    }
    if min_y < 0 {
        min_y = 0;
    }
    if max_y > height as isize {
        max_y = height as isize;
    }

    for y in min_y..max_y {
        for x in min_x..max_x {
            let dx = x as f32 - cx;
            let dy = y as f32 - cy;
            let dist = (dx * dx + dy * dy).sqrt();

            let idx = ((y as usize) * width + (x as usize)) * 4;

            // Inside main circle - solid color
            if dist <= radius {
                data[idx] = color.0;
                data[idx + 1] = color.1;
                data[idx + 2] = color.2;
                data[idx + 3] = 255;
            }
            // In glow region
            else if dist <= radius + glow_radius {
                let t = 1.0 - (dist - radius) / glow_radius;
                let alpha = (80.0 * t) as u8;
                data[idx] = color.0;
                data[idx + 1] = color.1;
                data[idx + 2] = color.2;
                data[idx + 3] = alpha;
            }
        }
    }
}

/// Fill an ellipse with alpha gradient
#[allow(clippy::too_many_arguments)]
fn fill_glow_ellipse(
    data: &mut [u8],
    width: usize,
    height: usize,
    cx: f32,
    cy: f32,
    rx: f32,
    ry: f32,
    color: RgbaColor,
    glow_alpha: u8,
) {
    let mut min_x = (cx - rx - 1.0) as isize;
    let mut max_x = (cx + rx + 1.0) as isize;
    let mut min_y = (cy - ry - 1.0) as isize;
    let mut max_y = (cy + ry + 1.0) as isize;

    if min_x < 0 {
        min_x = 0;
    }
    if max_x > width as isize {
        max_x = width as isize;
    }
    if min_y < 0 {
        min_y = 0;
    }
    if max_y > height as isize {
        max_y = height as isize;
    }

    let rx2 = rx * rx;
    let ry2 = ry * ry;

    for y in min_y..max_y {
        for x in min_x..max_x {
            let dx = x as f32 - cx;
            let dy = y as f32 - cy;
            let normalized = (dx * dx) / rx2 + (dy * dy) / ry2;

            if normalized <= 1.0 {
                let idx = ((y as usize) * width + (x as usize)) * 4;
                data[idx] = color.0;
                data[idx + 1] = color.1;
                data[idx + 2] = color.2;
                data[idx + 3] = glow_alpha;
            }
        }
    }
}

/// Create glow surface for a single bullet
/// Returns RGBA bytes
#[pyfunction]
pub fn create_single_bullet_glow(width: f32, height: f32) -> Vec<u8> {
    let surf_w = (width + 16.0) as usize;
    let surf_h = (height + 12.0) as usize;
    let cx = (surf_w as f32) / 2.0;
    let cy = (surf_h as f32) / 2.0;

    let mut data = vec![0u8; surf_w * surf_h * 4];

    // Create layered glow ellipses
    for i in (1..=6).rev() {
        let alpha = ((6 - i) * 30 / 5) as u8;
        let rx = width / 2.0 + (i as f32) * 1.0 - 3.0;
        let ry = height / 2.0 + (i as f32) * 0.5 - 1.0;
        let glow_color = RgbaColor(255, 200, 50);
        fill_glow_ellipse(
            &mut data,
            surf_w,
            surf_h,
            cx,
            cy + 2.0,
            rx,
            ry,
            glow_color,
            alpha,
        );
    }

    data
}

/// Create glow surface for a spread bullet
#[pyfunction]
pub fn create_spread_bullet_glow(radius: f32) -> Vec<u8> {
    let surf_size = (radius * 4.0 + 8.0) as usize;
    let cx = (surf_size as f32) / 2.0;
    let cy = (surf_size as f32) / 2.0;

    let mut data = vec![0u8; surf_size * surf_size * 4];

    let steps = (radius + 4.0) as isize;
    for i in (1..=steps).rev().step_by(2) {
        let alpha = ((steps - i) * 40 / steps) as u8;
        let r = i as f32;
        fill_glow_circle(
            &mut data,
            surf_size,
            surf_size,
            cx,
            cy,
            r + 2.0,
            RgbaColor(255, 150, 50),
            0.0,
        );
        // Manually set alpha
        let min_x = (cx - r - 2.0) as isize;
        let max_x = (cx + r + 2.0) as isize;
        let min_y = (cy - r - 2.0) as isize;
        let max_y = (cy + r + 2.0) as isize;
        for y in min_x.max(0)..max_x.min(surf_size as isize) {
            for x in min_y.max(0)..max_y.min(surf_size as isize) {
                let dx = x as f32 - cx;
                let dy = y as f32 - cy;
                let dist = (dx * dx + dy * dy).sqrt();
                if dist <= r + 2.0 && dist > r {
                    let idx = ((y as usize) * surf_size + (x as usize)) * 4;
                    data[idx + 3] = alpha;
                }
            }
        }
    }

    data
}

/// Create glow surface for a laser bullet
#[pyfunction]
pub fn create_laser_bullet_glow(height: f32) -> Vec<u8> {
    let surf_w = 24usize;
    let surf_h = (height + 12.0) as usize;
    let cx = 12.0f32;

    let mut data = vec![0u8; surf_w * surf_h * 4];

    for i in (1..=10).rev().step_by(2) {
        let alpha = ((10 - i) * 70 / 9) as u8;
        let thickness = i as f32;
        let glow_color = (255u8, 20u8, 40u8);
        let min_x = (cx - thickness / 2.0) as isize;
        let max_x = (cx + thickness / 2.0) as isize;
        let y_start = 4isize;
        let y_end = (surf_h as isize) - 4;
        for x in min_x..max_x {
            for y in y_start..y_end {
                let x_idx = x as usize;
                let y_idx = y as usize;
                if x_idx < surf_w && y_idx < surf_h {
                    let idx = (y_idx * surf_w + x_idx) * 4;
                    data[idx] = glow_color.0;
                    data[idx + 1] = glow_color.1;
                    data[idx + 2] = glow_color.2;
                    data[idx + 3] = alpha;
                }
            }
        }
    }

    data
}

/// Create glow surface for an explosive missile
#[pyfunction]
pub fn create_explosive_missile_glow(width: f32, height: f32) -> Vec<u8> {
    let bw = width * 0.8;
    let surf_w = (bw * 3.0 + 12.0) as usize;
    let surf_h = (height + 10.0) as usize;
    let cx = (surf_w as f32) / 2.0;

    let mut data = vec![0u8; surf_w * surf_h * 4];

    for i in (1..=6).rev() {
        let alpha = ((6 - i) * 35 / 5) as u8;
        let glow_color = RgbaColor(255, 80, 20);
        let rx = bw / 2.0 + (6 - i) as f32 * 2.0;
        let ry = height / 2.0 + (6 - i) as f32 * 2.0;
        fill_glow_ellipse(
            &mut data,
            surf_w,
            surf_h,
            cx,
            height / 2.0 + 5.0,
            rx,
            ry,
            glow_color,
            alpha,
        );
    }

    data
}

/// Create glow circle surface
#[pyfunction]
pub fn create_glow_circle(radius: i32, r: u8, g: u8, b: u8, glow_radius: i32) -> Vec<u8> {
    let surf_size = (radius + glow_radius) * 2 + 4;
    let surf_size = surf_size as usize;
    let cx = (surf_size as f32) / 2.0;
    let cy = (surf_size as f32) / 2.0;

    let mut data = vec![0u8; surf_size * surf_size * 4];

    // Draw solid circle
    fill_glow_circle(
        &mut data,
        surf_size,
        surf_size,
        cx,
        cy,
        radius as f32,
        RgbaColor(r, g, b),
        glow_radius as f32,
    );

    data
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_single_bullet_glow_size() {
        let data = create_single_bullet_glow(8.0, 16.0);
        let expected_w = (8.0 + 16.0) as usize;
        let expected_h = (16.0 + 12.0) as usize;
        assert_eq!(data.len(), expected_w * expected_h * 4);
    }

    #[test]
    fn test_glow_circle_size() {
        let data = create_glow_circle(10, 255, 0, 0, 5);
        let size = (10 + 5) * 2 + 4;
        assert_eq!(data.len(), (size as usize) * (size as usize) * 4);
    }
}
