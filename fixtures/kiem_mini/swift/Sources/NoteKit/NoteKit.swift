import Foundation

/// Extracts #tags from text. Currently only recognizes a tag when the whole
/// whitespace-delimited token starts with '#' — punctuation directly
/// touching a tag (e.g. "hello,#tag." or "(#tag)") is not recognized.
public func extractTags(from text: String) -> [String] {
    return text.split(separator: " ")
        .filter { $0.hasPrefix("#") }
        .map { String($0.dropFirst()) }
}
