// macOS Vision OCR helper.
// Usage: ocr_page <image.png>  -> JSON array of {t, conf, x, y, w, h}
// Coordinates are normalised to the image (origin top-left).
import Foundation
import Vision
import AppKit

guard CommandLine.arguments.count > 1 else {
    FileHandle.standardError.write("usage: ocr_page <image>\n".data(using: .utf8)!)
    exit(2)
}
let path = CommandLine.arguments[1]
guard let img = NSImage(contentsOfFile: path),
      let tiff = img.tiffRepresentation,
      let bmp = NSBitmapImageRep(data: tiff),
      let cg = bmp.cgImage else {
    FileHandle.standardError.write("cannot load \(path)\n".data(using: .utf8)!)
    exit(1)
}

let req = VNRecognizeTextRequest()
req.recognitionLevel = .accurate
req.usesLanguageCorrection = false
req.recognitionLanguages = ["ja-JP", "en-US"]

let handler = VNImageRequestHandler(cgImage: cg, options: [:])
try handler.perform([req])

var out: [[String: Any]] = []
for obs in (req.results ?? []) {
    guard let c = obs.topCandidates(1).first else { continue }
    let b = obs.boundingBox
    out.append([
        "t": c.string,
        "conf": c.confidence,
        "x": b.minX, "y": 1 - b.maxY, "w": b.width, "h": b.height,
    ])
}
let data = try JSONSerialization.data(withJSONObject: out, options: [])
FileHandle.standardOutput.write(data)
