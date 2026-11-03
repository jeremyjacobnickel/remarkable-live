package main

import "testing"

func TestParseRegionsKeepsOnlyLargeAnonymousWritable(t *testing.T) {
	maps := `aaab03c00000-aaab0b200000 rw-p 00000000 00:00 0                          [heap]
ffff46f70000-ffff47770000 rw-p 00000000 00:00 0
ffff753b3000-ffff767e0000 rw-p 00000000 00:00 0
ffff528c0000-ffff528e0000 rw-p 0000e000 00:01 3101                       /memfd:JSGCHeap:QtQml (deleted)
ffff7ee60000-ffff7f477000 r-xp 00000000 b3:02 1352                       /usr/lib/libicudata.so.78.3
`
	regions := parseRegions(maps)
	if len(regions) != 1 || regions[0] != [2]uint64{0xffff753b3000, 0xffff767e0000} {
		t.Fatalf("unerwartete Bereiche: %x", regions)
	}
}

func TestToImageCropsPaddingAndSwapsChannels(t *testing.T) {
	frame := make([]byte, frameBytes)
	frame[0], frame[1], frame[2], frame[3] = 0x10, 0x20, 0x30, 0xff // BGRA
	img := toImage(frame)
	if img.Bounds().Dx() != visibleWidth || img.Bounds().Dy() != height {
		t.Fatalf("Größe %v", img.Bounds())
	}
	if got := img.Pix[0:4]; got[0] != 0x30 || got[1] != 0x20 || got[2] != 0x10 || got[3] != 0xff {
		t.Fatalf("Pixel %x", got)
	}
}
