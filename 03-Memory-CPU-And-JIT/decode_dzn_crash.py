#!/usr/bin/env python3
"""Decode vulkan_dzn.dll+0x1fd79 from the 2026-11-10 hardware crash.

Usage:
    python3 decode_dzn_crash.py dozen-uwp.zip [--rva 0x1fd79] [--window 96]

Input: the `dozen-uwp` CI artifact zip (contains vulkan_dzn.dll built from
Cosmo/mesa_ai_slop_version@a76cd3c with MSVC 14.44, buildtype=release).
Crash line (loader-2026_11_10-2.log.txt:2003):
    UNHANDLED NATIVE FAULT: code=0xc0000005 module=vulkan_dzn.dll+0x1fd79
    rip=0x7ffbf210fd79 rsp=0xb301ff2a0 addr=0x150
=> faulting instruction is at RVA 0x1fd79; it dereferenced [NULL + 0x150].

This script: extracts the DLL, disassembles a window around the RVA with
capstone, marks the faulting instruction, and prints nearby string/rip-relative
references plus the export table (anchors). Pure forensics - no build required.
"""
import argparse
import io
import re
import sys
import zipfile

try:
    import pefile
    import capstone
except ImportError:
    sys.exit("needs: pip install pefile capstone")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("zip_path")
    ap.add_argument("--rva", default="0x1fd79")
    ap.add_argument("--window", type=int, default=96)
    ap.add_argument("--out", default="vulkan_dzn.dll")
    args = ap.parse_args()
    rva = int(args.rva, 16)

    with zipfile.ZipFile(args.zip_path) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith("vulkan_dzn.dll")]
        if not names:
            print("zip entries:", zf.namelist())
            sys.exit("vulkan_dzn.dll not found in zip")
        data = zf.read(names[0])
    print(f"loaded {names[0]}: {len(data)} bytes")
    open(args.out, "wb").write(data)

    pe = pefile.PE(data=data, fast_load=True)
    pe.parse_data_directories(
        directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]]
    )
    image_base = pe.OPTIONAL_HEADER.ImageBase
    print(f"ImageBase=0x{image_base:x}  fault VA=0x{image_base + rva:x}")

    exps = []
    if hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
        for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
            exps.append((e.address, e.name.decode() if e.name else f"ord{e.ordinal}"))
    exps.sort()
    print(f"exports: {len(exps)}")
    lo = [x for x in exps if x[0] <= rva]
    hi = [x for x in exps if x[0] > rva]
    if lo:
        print(f"  nearest export at/below: {lo[-1][1]} @ RVA 0x{lo[-1][0]:x} (+0x{rva - lo[-1][0]:x} into it)")
    if hi:
        print(f"  nearest export above:    {hi[0][1]} @ RVA 0x{hi[0][0]:x}")

    for sec in pe.sections:
        va, sz = sec.VirtualAddress, sec.Misc_VirtualSize
        if va <= rva < va + sz:
            name = sec.Name.rstrip(b"\x00").decode()
            off = pe.get_offset_from_rva(rva)
            raw = pe.get_memory_mapped_image()
            lo_off = max(va, rva - args.window)
            blob = raw[lo_off : rva + args.window]
            md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
            md.detail = True
            print(f"\nsection {name}: RVA 0x{va:x}+0x{sz:x}, fileoff 0x{off:x}")
            print(f"--- disassembly around 0x{rva:x} (>>> = faulting instruction) ---")
            for insn in md.disasm(blob, lo_off):
                mark = ">>>" if insn.address == rva else "   "
                note = ""
                if re.search(r"\[.*0x150.*\]", insn.op_str):
                    note = "   <=== reads field at +0x150"
                print(f"{mark} 0x{insn.address:x}: {insn.mnemonic:8s} {insn.op_str}{note}")
            break

    print("\ninterpretation notes:")
    print("  * 'addr=0x150' = the faulting instruction read [NULL + 0x150]:")
    print("    a field at offset 0x150 of an object pointer that was NULL.")
    print("  * match the marked instruction's register source to the callee-saved")
    print("    register holding a per-object pointer to identify the struct; then")
    print("    grep the dzn sources (pin a76cd3c) for that field.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
