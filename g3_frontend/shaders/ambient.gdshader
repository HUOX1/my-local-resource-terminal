shader_type spatial;
render_mode unshaded, cull_disabled;

uniform vec3 top_color : source_color = vec3(0.035, 0.025, 0.075);
uniform vec3 bottom_color : source_color = vec3(0.004, 0.008, 0.030);
uniform vec3 wave_a : source_color = vec3(0.62, 0.16, 0.92);
uniform vec3 wave_b : source_color = vec3(0.12, 0.52, 1.00);
uniform vec3 symbol_color : source_color = vec3(0.88, 0.84, 1.00);
uniform float symbol_amount : hint_range(0.0, 1.0) = 0.34;
uniform float wave_amount : hint_range(0.0, 1.0) = 0.72;

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
    y += sin(uv.x * (freq * 0.53) - phase * 0.71) * amp * 0.28;
    float d = abs(uv.y - y);
    return 1.0 - smoothstep(thickness, thickness * 2.4, d);
}

void fragment() {
    vec2 uv = UV;
    float aspect = VIEWPORT_SIZE.x / max(VIEWPORT_SIZE.y, 1.0);
    vec3 col = mix(bottom_color, top_color, pow(1.0 - uv.y, 0.78));

    float w1 = wave_mask(uv, TIME * 0.48, 0.46, 0.070, 6.4, 0.026);
    float w2 = wave_mask(uv, -TIME * 0.36 + 1.7, 0.54, 0.090, 5.0, 0.032);
    float w3 = wave_mask(uv, TIME * 0.27 + 3.2, 0.61, 0.060, 8.2, 0.022);
    col += wave_a * w1 * 0.080 * wave_amount;
    col += wave_b * w2 * 0.070 * wave_amount;
    col += mix(wave_a, wave_b, 0.48) * w3 * 0.048 * wave_amount;

    vec2 p = vec2(uv.x * aspect, uv.y);
    float symbol_alpha = 0.0;
    for (int i = 0; i < 24; i++) {
        float fi = float(i) + 1.0;
        float rx = hash11(fi * 1.13);
        float ry = hash11(fi * 2.71);
        float rs = hash11(fi * 4.37);
        float rv = hash11(fi * 6.19);
        float rr = hash11(fi * 8.53);
        vec2 home = vec2(rx * aspect, ry);
        float drift_x = (rv - 0.5) * 0.024;
        float drift_y = 0.014 + hash11(fi * 9.91) * 0.026;
        vec2 drift = vec2(sin(TIME * (0.13 + rv * 0.15) + fi) * drift_x, -TIME * drift_y);
        vec2 pos = home + drift;
        pos.y = fract(pos.y + 1.25);
        pos.x += sin(TIME * 0.12 + fi * 2.1) * 0.014;
        vec2 lp = rot2(p - pos, (rr - 0.5) * 1.5 + TIME * (rr - 0.5) * 0.08);
        float radius = 0.007 + rs * 0.006;
        float d = symbol_distance(lp, i % 4, radius);
        float stroke = 0.00085 + radius * 0.050;
        float line = 1.0 - smoothstep(stroke, stroke * 2.1, d);
        symbol_alpha += line * mix(0.15, 0.52, rs);
    }
    symbol_alpha = clamp(symbol_alpha, 0.0, 1.0);
    col += symbol_color * symbol_alpha * 0.16 * symbol_amount;

    vec2 edge = abs(uv - vec2(0.5)) * 2.0;
    float vignette = smoothstep(0.68, 1.22, max(edge.x, edge.y));
    col *= 1.0 - vignette * 0.24;
    ALBEDO = col;
}
