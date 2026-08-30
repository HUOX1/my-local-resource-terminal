shader_type canvas_item;
render_mode unshaded;

uniform vec3 top_color : source_color = vec3(0.035, 0.025, 0.075);
uniform vec3 bottom_color : source_color = vec3(0.004, 0.008, 0.030);
uniform vec3 wave_a : source_color = vec3(0.62, 0.16, 0.92);
uniform vec3 wave_b : source_color = vec3(0.12, 0.52, 1.00);
uniform vec3 symbol_color : source_color = vec3(0.88, 0.84, 1.00);
uniform float symbol_amount : hint_range(0.0, 1.0) = 0.42;
uniform float wave_amount : hint_range(0.0, 1.0) = 0.82;

float hash11(float p) {
    return fract(sin(p * 127.1 + 311.7) * 43758.5453123);
}

vec2 rot2(vec2 p, float a) {
    float c = cos(a);
    float s = sin(a);
    return vec2(c * p.x - s * p.y, s * p.x + c * p.y);
}

float segment_distance(vec2 p, vec2 a, vec2 b) {
    vec2 pa = p - a;
    vec2 ba = b - a;
    float h = clamp(dot(pa, ba) / max(dot(ba, ba), 0.00001), 0.0, 1.0);
    return length(pa - ba * h);
}

float circle_outline(vec2 p, float r) {
    return abs(length(p) - r);
}

float box_outline(vec2 p, vec2 b) {
    vec2 q = abs(p) - b;
    float sd = length(max(q, vec2(0.0))) + min(max(q.x, q.y), 0.0);
    return abs(sd);
}

float triangle_outline(vec2 p, float r) {
    vec2 a = vec2(0.0, -r);
    vec2 b = vec2(-r * 0.87, r * 0.56);
    vec2 c = vec2(r * 0.87, r * 0.56);
    return min(segment_distance(p, a, b), min(segment_distance(p, b, c), segment_distance(p, c, a)));
}

float x_outline(vec2 p, float r) {
    float d1 = segment_distance(p, vec2(-r, -r), vec2(r, r));
    float d2 = segment_distance(p, vec2(-r, r), vec2(r, -r));
    return min(d1, d2);
}

float symbol_distance(vec2 p, int kind, float r) {
    if (kind == 0) return triangle_outline(p, r);
    if (kind == 1) return circle_outline(p, r * 0.78);
    if (kind == 2) return box_outline(p, vec2(r * 0.68));
    return x_outline(p, r * 0.72);
}

float wave_mask(vec2 uv, float phase, float y_base, float amp, float freq, float thickness) {
    float y = y_base;
    y += sin(uv.x * freq + phase) * amp;
    y += sin(uv.x * (freq * 0.53) - phase * 0.71) * amp * 0.36;
    float d = abs(uv.y - y);
    return 1.0 - smoothstep(thickness, thickness * 2.7, d);
}

void fragment() {
    vec2 uv = UV;
    float aspect = SCREEN_PIXEL_SIZE.y / max(SCREEN_PIXEL_SIZE.x, 0.000001);
    vec3 col = mix(bottom_color, top_color, pow(1.0 - uv.y, 0.78));

    vec2 glow_p = uv - vec2(0.52, 0.45);
    glow_p.x *= aspect;
    float glow = exp(-dot(glow_p, glow_p) * 2.6);
    col += mix(wave_b, wave_a, 0.58) * glow * 0.075;

    float w1 = wave_mask(uv, TIME * 0.58, 0.45, 0.085, 7.2, 0.028);
    float w2 = wave_mask(uv, -TIME * 0.42 + 1.7, 0.52, 0.105, 5.6, 0.036);
    float w3 = wave_mask(uv, TIME * 0.31 + 3.2, 0.59, 0.072, 9.1, 0.024);
    float w4 = wave_mask(uv, -TIME * 0.23 + 0.8, 0.66, 0.055, 11.4, 0.020);
    col += wave_a * w1 * 0.10 * wave_amount;
    col += wave_b * w2 * 0.085 * wave_amount;
    col += mix(wave_a, wave_b, 0.48) * w3 * 0.060 * wave_amount;
    col += mix(wave_b, vec3(0.9, 0.32, 0.75), 0.35) * w4 * 0.045 * wave_amount;

    vec2 p = vec2(uv.x * aspect, uv.y);
    float symbol_alpha = 0.0;
    for (int i = 0; i < 36; i++) {
        float fi = float(i) + 1.0;
        float rx = hash11(fi * 1.13);
        float ry = hash11(fi * 2.71);
        float rs = hash11(fi * 4.37);
        float rv = hash11(fi * 6.19);
        float rr = hash11(fi * 8.53);
        vec2 home = vec2(rx * aspect, ry);
        float drift_x = (rv - 0.5) * 0.035;
        float drift_y = 0.018 + hash11(fi * 9.91) * 0.038;
        vec2 drift = vec2(sin(TIME * (0.16 + rv * 0.18) + fi) * drift_x, -TIME * drift_y);
        vec2 pos = home + drift;
        pos.y = fract(pos.y + 1.25);
        pos.x += sin(TIME * 0.14 + fi * 2.1) * 0.018;
        vec2 lp = rot2(p - pos, (rr - 0.5) * 1.8 + TIME * (rr - 0.5) * 0.11);
        float radius = 0.007 + rs * 0.007;
        float d = symbol_distance(lp, i % 4, radius);
        float stroke = 0.00085 + radius * 0.055;
        float line = 1.0 - smoothstep(stroke, stroke * 2.2, d);
        symbol_alpha += line * mix(0.17, 0.62, rs);
    }
    symbol_alpha = clamp(symbol_alpha, 0.0, 1.0);
    col += symbol_color * symbol_alpha * 0.20 * symbol_amount;

    vec2 edge = abs(uv - vec2(0.5)) * 2.0;
    float vignette = smoothstep(0.62, 1.26, max(edge.x, edge.y));
    col *= 1.0 - vignette * 0.30;
    COLOR = vec4(col, 1.0);
}
