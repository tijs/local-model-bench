// Verify the diagnostic behavior of the actual Swift runtime without MLX/model work.
let keys = (0..<32).map { "parameter.\($0)" }
print(keys.map { String($0.hashValue) }.joined(separator: ","))
print(Dictionary(uniqueKeysWithValues: keys.map { ($0, 0) }).keys.joined(separator: ","))
