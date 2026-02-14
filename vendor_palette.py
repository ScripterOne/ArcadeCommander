VENDOR_PALETTES = {
    "Nintendo": {"p1": "#E60012", "p2": "#00A0E9", "system": "#FFFFFF"},
    "Capcom": {"p1": "#0B4EA2", "p2": "#FFD100", "system": "#FFFFFF"},
    "Sega": {"p1": "#0055A4", "p2": "#E6002D", "system": "#FFFFFF"},
    "Konami": {"p1": "#E4002B", "p2": "#0072CE", "system": "#FFFFFF"},
    "Atari": {"p1": "#D52B1E", "p2": "#4B4F54", "system": "#FFFFFF"},
    "Namco": {"p1": "#E60012", "p2": "#FFB81C", "system": "#FFFFFF"},
    "Midway": {"p1": "#0057B8", "p2": "#E2231A", "system": "#FFFFFF"},
    "Williams": {"p1": "#003DA5", "p2": "#E03C31", "system": "#FFFFFF"},
    "SNK": {"p1": "#00A4E4", "p2": "#FF5F1F", "system": "#FFFFFF"},
    "Taito": {"p1": "#005BAC", "p2": "#E4002B", "system": "#FFFFFF"},
    "Data East": {"p1": "#1B5EAA", "p2": "#F26621", "system": "#FFFFFF"},
}

def hex_to_rgb_tuple(hex_color):
    if not hex_color:
        return None
    h = hex_color.strip()
    if not h.startswith("#") or len(h) != 7:
        return None
    try:
        r = int(h[1:3], 16)
        g = int(h[3:5], 16)
        b = int(h[5:7], 16)
        return (r, g, b)
    except Exception:
        return None

def rgb_tuple_to_str(rgb):
    if not rgb or len(rgb) != 3:
        return None
    return f"{int(rgb[0])},{int(rgb[1])},{int(rgb[2])}"

def dim_rgb(rgb, factor):
    if not rgb:
        return None
    r = max(0, min(255, int(rgb[0] * factor)))
    g = max(0, min(255, int(rgb[1] * factor)))
    b = max(0, min(255, int(rgb[2] * factor)))
    return (r, g, b)

def get_vendor_colors(vendor_name):
    if not vendor_name:
        return None
    palette = VENDOR_PALETTES.get(vendor_name)
    if not palette:
        return None

    p1_hex = palette.get("p1")
    p2_hex = palette.get("p2")
    sys_hex = palette.get("system")

    p1_rgb = hex_to_rgb_tuple(p1_hex)
    if not p1_rgb:
        return None

    p2_rgb = hex_to_rgb_tuple(p2_hex) if p2_hex else dim_rgb(p1_rgb, 0.75)
    sys_rgb = hex_to_rgb_tuple(sys_hex) if sys_hex else dim_rgb(p1_rgb, 0.6)

    return {
        "p1": rgb_tuple_to_str(p1_rgb),
        "p2": rgb_tuple_to_str(p2_rgb),
        "system": rgb_tuple_to_str(sys_rgb),
    }
