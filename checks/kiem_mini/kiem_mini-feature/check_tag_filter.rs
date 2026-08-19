use notekeep::{filter_by_tag, Note};

fn note(id: &str, tags: &[&str]) -> Note {
    Note {
        id: id.to_string(),
        title: id.to_string(),
        body: String::new(),
        tags: tags.iter().map(|s| s.to_string()).collect(),
    }
}

#[test]
fn filters_by_tag() {
    let notes = vec![
        note("a", &["work", "urgent"]),
        note("b", &["personal"]),
        note("c", &["work"]),
    ];
    let filtered = filter_by_tag(&notes, "work");
    let ids: Vec<&str> = filtered.iter().map(|n| n.id.as_str()).collect();
    assert_eq!(ids, vec!["a", "c"]);
}

#[test]
fn empty_when_no_match() {
    let notes = vec![note("a", &["work"])];
    assert!(filter_by_tag(&notes, "nonexistent").is_empty());
}
