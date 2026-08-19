use notekeep::extract_tags;

#[test]
fn extracts_simple_tags() {
    assert_eq!(extract_tags("hello #world #rust"), vec!["world", "rust"]);
}

#[test]
fn no_tags_when_none_present() {
    assert_eq!(extract_tags("just plain text"), Vec::<String>::new());
}
