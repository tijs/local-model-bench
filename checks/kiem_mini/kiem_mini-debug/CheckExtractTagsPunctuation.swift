import Testing
@testable import NoteKit

@Test func handlesPunctuationAdjacentTags() {
    #expect(extractTags(from: "hello,#tag.") == ["tag"])
    #expect(extractTags(from: "(#foo)") == ["foo"])
    #expect(extractTags(from: "multiple #one,#two;#three") == ["one", "two", "three"])
}

@Test func stillHandlesPlainTags() {
    #expect(extractTags(from: "plain #simple text") == ["simple"])
    #expect(extractTags(from: "no tags here") == [])
}
