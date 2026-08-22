import Foundation

/// Extracts #tags from a note's body text, in the order they appear.
public func extractTags(from text: String) -> [String] {
    return text.split(separator: " ")
        .filter { $0.hasPrefix("#") }
        .map { String($0.dropFirst()) }
}

public struct Note: Equatable {
    public let id: String
    public let title: String
    public let body: String
    public let tags: [String]
    public let pinned: Bool
}
