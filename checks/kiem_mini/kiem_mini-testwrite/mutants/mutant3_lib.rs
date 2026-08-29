pub mod store;

#[derive(Debug, Clone, PartialEq)]
pub struct Note {
    pub id: String,
    pub title: String,
    pub body: String,
    pub tags: Vec<String>,
    pub pinned: bool,
}

/// Sets `pinned = true` on the note matching `id`, if any.
pub fn pin(notes: &mut [Note], id: &str) {
    if let Some(n) = notes.iter_mut().find(|n| n.id == id) {
        n.pinned = true;
    }
}

/// Sets `pinned = false` on the note matching `id`, if any.
pub fn unpin(notes: &mut [Note], id: &str) {
    if let Some(n) = notes.iter_mut().find(|n| n.id == id) {
        n.pinned = false;
    }
}

/// BUG (mutant 3): partitions pinned-first correctly, but sorts each group
/// by id instead of preserving relative order — a test that only checks
/// "every pinned note comes before every unpinned note" (without checking
/// order WITHIN each group) will not catch this.
pub fn ordered_pinned_first(notes: &[Note]) -> Vec<&Note> {
    let mut pinned: Vec<&Note> = notes.iter().filter(|n| n.pinned).collect();
    let mut rest: Vec<&Note> = notes.iter().filter(|n| !n.pinned).collect();
    pinned.sort_by(|a, b| a.id.cmp(&b.id));
    rest.sort_by(|a, b| a.id.cmp(&b.id));
    pinned.append(&mut rest);
    pinned
}

/// Extracts #tags from text. Currently only recognizes a tag when the
/// whole whitespace-delimited token starts with '#' — punctuation directly
/// touching a tag (e.g. "hello,#tag." or "(#tag)") is not recognized.
pub fn extract_tags(text: &str) -> Vec<String> {
    text.split_whitespace()
        .filter(|tok| tok.starts_with('#'))
        .map(|tok| tok.trim_start_matches('#').to_string())
        .collect()
}

pub fn new_note(id: &str, title: &str, body: &str) -> Note {
    Note {
        id: id.to_string(),
        title: title.to_string(),
        body: body.to_string(),
        tags: extract_tags(body),
        pinned: false,
    }
}
