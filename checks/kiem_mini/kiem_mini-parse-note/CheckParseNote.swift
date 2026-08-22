import Testing
@testable import NoteKit

@Test func parsesAWellFormedNote() throws {
    let text = "note-1\n---\nShopping\n---\n1\n---\nmilk #urgent eggs"
    let note = try parseNote(from: text)
    #expect(note.id == "note-1")
    #expect(note.title == "Shopping")
    #expect(note.pinned == true)
    #expect(note.body == "milk #urgent eggs")
    #expect(note.tags == ["urgent"])
}

@Test func unpinnedFlagIsFalse() throws {
    let text = "note-2\n---\nIdeas\n---\n0\n---\nno tags here"
    let note = try parseNote(from: text)
    #expect(note.pinned == false)
    #expect(note.tags == [])
}

@Test func malformedInputThrowsRatherThanCrashingOrGuessing() {
    let tooFewParts = "note-3\n---\nonly two parts"
    #expect(throws: NoteParseError.malformedFormat) {
        try parseNote(from: tooFewParts)
    }

    let tooManyParts = "a\n---\nb\n---\nc\n---\nd\n---\ne"
    #expect(throws: NoteParseError.malformedFormat) {
        try parseNote(from: tooManyParts)
    }
}
