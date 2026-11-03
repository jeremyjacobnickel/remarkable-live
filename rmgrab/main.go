// rmgrab läuft auf dem reMarkable Paper Pro und schreibt den aktuellen
// Bildschirminhalt als PNG nach stdout.
//
// Quelle ist der Qt-Bildpuffer von xochitl (1632×2160, BGRA, Zeilenbreite
// 6528 Byte). Er liegt als per mmap angelegter malloc-Chunk im Speicher von
// xochitl; seine Adresse ändert sich bei jedem Start und wird daher gesucht
// und in /tmp zwischengespeichert.
package main

import (
	"bufio"
	"encoding/binary"
	"errors"
	"fmt"
	"image"
	"image/png"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

const (
	bufferWidth   = 1632
	visibleWidth  = 1620
	height        = 2160
	stride        = bufferWidth * 4
	frameBytes    = stride * height
	chunkHeader   = 16
	pageSize      = 4096
	mmappedFlag   = 0x2
	maxChunkSlack = 64 * 1024
	cachePath     = "/tmp/rmgrab.cache"
)

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, "rmgrab:", err)
		os.Exit(1)
	}
}

func run() error {
	pid, err := findXochitl()
	if err != nil {
		return err
	}
	mem, err := os.Open(fmt.Sprintf("/proc/%d/mem", pid))
	if err != nil {
		return err
	}
	defer mem.Close()

	addr, ok := cachedAddress(pid, mem)
	if !ok {
		if addr, err = findFramebuffer(pid, mem); err != nil {
			return err
		}
		os.WriteFile(cachePath, []byte(fmt.Sprintf("%d %d\n", pid, addr)), 0o600)
	}

	frame := make([]byte, frameBytes)
	if _, err := mem.ReadAt(frame, int64(addr)); err != nil {
		return fmt.Errorf("Bildpuffer lesen: %w", err)
	}
	out := bufio.NewWriter(os.Stdout)
	encoder := png.Encoder{CompressionLevel: png.BestSpeed}
	if err := encoder.Encode(out, toImage(frame)); err != nil {
		return err
	}
	return out.Flush()
}

func findXochitl() (int, error) {
	comms, _ := filepath.Glob("/proc/[0-9]*/comm")
	for _, path := range comms {
		name, err := os.ReadFile(path)
		if err == nil && strings.TrimSpace(string(name)) == "xochitl" {
			return strconv.Atoi(filepath.Base(filepath.Dir(path)))
		}
	}
	return 0, errors.New("xochitl läuft nicht")
}

func cachedAddress(pid int, mem *os.File) (uint64, bool) {
	data, err := os.ReadFile(cachePath)
	if err != nil {
		return 0, false
	}
	var cachedPid int
	var addr uint64
	if _, err := fmt.Sscan(string(data), &cachedPid, &addr); err != nil || cachedPid != pid {
		return 0, false
	}
	return addr, isFramebuffer(mem, addr-chunkHeader)
}

// findFramebuffer prüft jede Seite anonymer Speicherbereiche auf einen
// mmap-Chunk passender Größe, dessen Pixel deckend (Alpha 255) sind. Das
// unterscheidet den Qt-Puffer vom ähnlich großen Puffer des E-Ink-Treibers.
func findFramebuffer(pid int, mem *os.File) (uint64, error) {
	regions, err := anonymousRegions(pid)
	if err != nil {
		return 0, err
	}
	for _, r := range regions {
		for page := r[0]; page+chunkHeader+frameBytes <= r[1]; page += pageSize {
			if isFramebuffer(mem, page) {
				return page + chunkHeader, nil
			}
		}
	}
	return 0, errors.New("Bildpuffer nicht gefunden")
}

func anonymousRegions(pid int) ([][2]uint64, error) {
	data, err := os.ReadFile(fmt.Sprintf("/proc/%d/maps", pid))
	if err != nil {
		return nil, err
	}
	return parseRegions(string(data)), nil
}

// parseRegions liefert anonyme, beschreibbare Bereiche, in die ein Bild passt.
func parseRegions(maps string) [][2]uint64 {
	var regions [][2]uint64
	for _, line := range strings.Split(maps, "\n") {
		fields := strings.Fields(line)
		if len(fields) != 5 || fields[1] != "rw-p" {
			continue
		}
		bounds := strings.SplitN(fields[0], "-", 2)
		start, err1 := strconv.ParseUint(bounds[0], 16, 64)
		end, err2 := strconv.ParseUint(bounds[1], 16, 64)
		if err1 == nil && err2 == nil && end-start >= chunkHeader+frameBytes {
			regions = append(regions, [2]uint64{start, end})
		}
	}
	return regions
}

func isFramebuffer(mem *os.File, chunk uint64) bool {
	header := make([]byte, chunkHeader)
	if _, err := mem.ReadAt(header, int64(chunk)); err != nil {
		return false
	}
	prevSize := binary.LittleEndian.Uint64(header[0:8])
	size := binary.LittleEndian.Uint64(header[8:16])
	payload := (size &^ 7) - chunkHeader
	if prevSize != 0 || size&mmappedFlag == 0 || payload < frameBytes || payload > frameBytes+maxChunkSlack {
		return false
	}
	// Stichprobe: in jeder 97. Zeile ein Pixel prüfen.
	pixel := make([]byte, 4)
	for row := 0; row < height; row += 97 {
		offset := int64(chunk) + chunkHeader + int64(row*stride+(row%visibleWidth)*4)
		if _, err := mem.ReadAt(pixel, offset); err != nil || pixel[3] != 0xff {
			return false
		}
	}
	return true
}

// toImage schneidet die Polsterung rechts ab und dreht BGRA nach RGBA.
func toImage(frame []byte) *image.RGBA {
	img := image.NewRGBA(image.Rect(0, 0, visibleWidth, height))
	for y := 0; y < height; y++ {
		src := frame[y*stride : y*stride+visibleWidth*4]
		dst := img.Pix[y*img.Stride : y*img.Stride+visibleWidth*4]
		for x := 0; x < len(src); x += 4 {
			dst[x], dst[x+1], dst[x+2], dst[x+3] = src[x+2], src[x+1], src[x], 0xff
		}
	}
	return img
}
