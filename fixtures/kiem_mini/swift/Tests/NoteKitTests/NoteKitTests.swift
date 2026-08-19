import Testing
@testable import NoteKit

@Test func extractTagsSimple() {
    #expect(extractTags(from: "hello #world #swift") == ["world", "swift"])
}

@Test func extractTagsNoneWhenAbsent() {
    #expect(extractTags(from: "just plain text") == [])
}
