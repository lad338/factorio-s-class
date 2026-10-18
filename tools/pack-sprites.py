import struct, zlib, sys, os

def read_png(path):
    with open(path, "rb") as f:
        data = f.read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos = 8
    width = height = bit_depth = color_type = None
    idat = b""
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos+4])[0]
        ctype = data[pos+4:pos+8]
        cdata = data[pos+8:pos+8+length]
        pos += 8 + length + 4
        if ctype == b"IHDR":
            width, height, bit_depth, color_type = struct.unpack(">IIBB", cdata[:10])
        elif ctype == b"IDAT":
            idat += cdata
        elif ctype == b"IEND":
            break
    assert bit_depth == 8, f"unsupported bit depth {bit_depth}"
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color_type]
    raw = zlib.decompress(idat)
    stride = width * channels
    rows = []
    prev = bytearray(stride)
    i = 0
    for y in range(height):
        filt = raw[i]
        i += 1
        line = bytearray(raw[i:i+stride])
        i += stride
        for x in range(stride):
            a = line[x - channels] if x >= channels else 0
            b = prev[x]
            c = prev[x - channels] if x >= channels else 0
            if filt == 0:
                pass
            elif filt == 1:
                line[x] = (line[x] + a) & 0xFF
            elif filt == 2:
                line[x] = (line[x] + b) & 0xFF
            elif filt == 3:
                line[x] = (line[x] + ((a + b) // 2)) & 0xFF
            elif filt == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 0xFF
            else:
                raise ValueError(f"bad filter {filt}")
        rows.append(line)
        prev = line
    return width, height, channels, rows


def write_png(path, width, height, channels, rows):
    color_type = {1: 0, 2: 2, 3: 3, 4: 6}[channels]
    raw = bytearray()
    for row in rows:
        raw.append(0)
        raw.extend(row)
    compressed = zlib.compress(bytes(raw), 9)

    def chunk(ctype, cdata):
        out = struct.pack(">I", len(cdata)) + ctype + cdata
        crc = zlib.crc32(ctype + cdata) & 0xFFFFFFFF
        return out + struct.pack(">I", crc)

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)))
        f.write(chunk(b"IDAT", compressed))
        f.write(chunk(b"IEND", b""))


def pack_sheet(frame_dir, out_path, frame_size, grid, count):
    rows_out = [bytearray(frame_size * grid * 4) for _ in range(frame_size * grid)]
    for i in range(count):
        path = os.path.join(frame_dir, f"frame_{i:02d}.png")
        w, h, ch, rows = read_png(path)
        assert (w, h, ch) == (frame_size, frame_size, 4), f"{path}: {w}x{h}x{ch}"
        gx, gy = i % grid, i // grid
        for y in range(frame_size):
            dst_row = rows_out[gy * frame_size + y]
            src_row = rows[y]
            dst_off = gx * frame_size * 4
            dst_row[dst_off:dst_off + frame_size * 4] = src_row
    write_png(out_path, frame_size * grid, frame_size * grid, 4, rows_out)
    print(f"wrote {out_path}: {frame_size * grid}x{frame_size * grid}")


def content_bbox(rows, w, h, margin_frac=0.2):
    # Alpha bounding box of the opaque content, expanded by a margin and
    # squared off -- lets icons crop tight around the subject instead of
    # downscaling the whole frame (which includes padding needed to
    # avoid clipping the widest rotation, making the subject look small).
    min_x, max_x, min_y, max_y = w, 0, h, 0
    for y in range(h):
        row = rows[y]
        for x in range(w):
            if row[x * 4 + 3] > 0:
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)
    cx, cy = (min_x + max_x) / 2, (min_y + max_y) / 2
    size = max(max_x - min_x, max_y - min_y) * (1 + margin_frac)
    half = size / 2
    x0 = max(0, int(cx - half))
    y0 = max(0, int(cy - half))
    crop_size = min(w - x0, h - y0, int(size))
    return x0, y0, crop_size


def resize_area(rows, w, h, out_size):
    # Downscale via float-precision box averaging -- crop sizes aren't
    # chosen to divide evenly into out_size, so this can't use a simple
    # integer block ratio.
    out_rows = []
    scale = w / out_size
    for oy in range(out_size):
        sy0, sy1 = oy * scale, (oy + 1) * scale
        out_row = bytearray(out_size * 4)
        for ox in range(out_size):
            sx0, sx1 = ox * scale, (ox + 1) * scale
            r = g = b = a = wsum = 0.0
            iy0, iy1 = int(sy0), min(h, int(sy1) + 1)
            ix0, ix1 = int(sx0), min(w, int(sx1) + 1)
            for sy in range(iy0, iy1):
                wy = min(sy + 1, sy1) - max(sy, sy0)
                if wy <= 0:
                    continue
                row = rows[sy]
                for sx in range(ix0, ix1):
                    wx = min(sx + 1, sx1) - max(sx, sx0)
                    if wx <= 0:
                        continue
                    weight = wx * wy
                    px = sx * 4
                    r += row[px] * weight
                    g += row[px + 1] * weight
                    b += row[px + 2] * weight
                    a += row[px + 3] * weight
                    wsum += weight
            o = ox * 4
            if wsum > 0:
                out_row[o] = round(r / wsum)
                out_row[o + 1] = round(g / wsum)
                out_row[o + 2] = round(b / wsum)
                out_row[o + 3] = round(a / wsum)
        out_rows.append(out_row)
    return out_rows


def crop_and_resize(src_path, out_path, out_size, margin_frac=0.2):
    w, h, ch, rows = read_png(src_path)
    assert ch == 4
    x0, y0, crop_size = content_bbox(rows, w, h, margin_frac)
    cropped = [bytearray(row[x0 * 4:(x0 + crop_size) * 4]) for row in rows[y0:y0 + crop_size]]
    out_rows = resize_area(cropped, crop_size, crop_size, out_size)
    write_png(out_path, out_size, out_size, 4, out_rows)
    print(f"wrote {out_path}: {out_size}x{out_size} (cropped from {crop_size}x{crop_size} at {x0},{y0})")


if __name__ == "__main__":
    frame_dir = sys.argv[1]
    out_dir = sys.argv[2]
    frame_size = int(sys.argv[3])
    grid = int(sys.argv[4])
    count = int(sys.argv[5])

    os.makedirs(out_dir, exist_ok=True)
    pack_sheet(frame_dir, os.path.join(out_dir, "s-class-spritesheet.png"), frame_size, grid, count)
    pack_sheet(os.path.join(frame_dir, "shadow"), os.path.join(out_dir, "s-class-spritesheet-shadow.png"), frame_size, grid, count)

    # No map icon or tech icon needed: this entity relies on car-type's
    # built-in minimap fallback, and there's no new technology prototype.
    icon_dir = os.path.join(out_dir, "..", "..", "icons")
    os.makedirs(icon_dir, exist_ok=True)
    icon_source = os.path.join(frame_dir, "icon_source.png")  # dedicated southeast-facing render
    crop_and_resize(icon_source, os.path.join(icon_dir, "s-class-icon.png"), 64)
