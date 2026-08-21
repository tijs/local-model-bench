use notekeep::{filter_by_tag, Note};

fn note(id: &str, tags: &[&str]) -> Note {
    Note {
        id: id.to_string(),
        title: id.to_string(),
        body: String::new(),
        tags: tags.iter().map(|s| s.to_string()).collect(),
        pinned: false,
    }
}

#[test]
fn filters_by_tag() {
    let notes = vec![
        note("a", &["work", "urgent"]),
        note("b", &["personal"]),
        note("c", &["work"]),
    ];
    // Explicit type annotation forces the real signature: an
    // implementation that returns Vec<Note> (a clone) instead of
    // Vec<&'a Note> fails to COMPILE here, instead of silently passing
    // because `.id.as_str()` alone can't distinguish an owned Note from a
    // borrowed &Note.
    let filtered: Vec<&Note> = filter_by_tag(&notes, "work");
    let ids: Vec<&str> = filtered.iter().map(|n| n.id.as_str()).collect();
    assert_eq!(ids, vec!["a", "c"]);

    // Proves these are real references into `notes`, not clones that
    // happen to satisfy the type annotation above (e.g. a Vec<Note>
    // pushed through `.iter().collect()` after the fact). Pointer
    // identity is the only thing a clone can't fake.
    assert!(std::ptr::eq(filtered[0], &notes[0]));
    assert!(std::ptr::eq(filtered[1], &notes[2]));
}

#[test]
fn exact_match_not_substring() {
    // "homework" contains "work" as a substring but must NOT match a
    // filter for "work" — the prompt explicitly requires exact match, not
    // substring. Without this case, `tags.iter().any(|t| t.contains(tag))`
    // passes every other test in this file.
    let notes = vec![
        note("a", &["work"]),
        note("b", &["homework"]),
        note("c", &["work", "homework"]),
        note("d", &["ework"]),
    ];
    let filtered: Vec<&Note> = filter_by_tag(&notes, "work");
    let ids: Vec<&str> = filtered.iter().map(|n| n.id.as_str()).collect();
    assert_eq!(
        ids,
        vec!["a", "c"],
        "substring match incorrectly included/excluded a note (\"homework\"/\"ework\" must not match \"work\"): {ids:?}"
    );
}

#[test]
fn empty_when_no_match() {
    let notes = vec![note("a", &["work"])];
    assert!(filter_by_tag(&notes, "nonexistent").is_empty());
}

#[test]
fn preserves_relative_order_with_gaps_and_repeats() {
    let notes = vec![
        note("a", &["work"]),
        note("b", &["other"]),
        note("c", &["work"]),
        note("d", &["work"]),
        note("e", &["other"]),
    ];
    let filtered: Vec<&Note> = filter_by_tag(&notes, "work");
    let ids: Vec<&str> = filtered.iter().map(|n| n.id.as_str()).collect();
    assert_eq!(ids, vec!["a", "c", "d"]);
}
