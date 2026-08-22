import Foundation

/// Extracts #tags from a note's body text, in the order they appear.
public func extractTags(from text: String) -> [String] {
    return text.split(separator: " ")
        .filter { $0.hasPrefix("#") }
        .map { String($0.dropFirst()) }
}
