// Explicitly enabled in an otherwise extension-free Pi session. Only the trusted
// runner can resolve file names, save snapshots, and execute fixture checks.
import { Type } from "typebox";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

async function call(action: string, args: unknown) {
  const response = await fetch(process.env.CODING_BRIDGE!, {
    method: "POST", headers: {
      Authorization: "Bearer " + process.env.CODING_TOKEN!,
      "Content-Type": "application/json",
    }, body: JSON.stringify({ action, args }),
  });
  if (!response.ok) throw new Error(await response.text());
  return await response.json();
}
export default function(pi: ExtensionAPI) {
  const path = Type.String({ description: "An exact filename listed in the task." });
  const tools = [
    ["read_file", "Read a task file.", Type.Object({path})],
    ["write_file", "Replace a task file with its complete new source.", Type.Object({path, content: Type.String()})],
    ["edit_file", "Replace one exact, unique substring in a task file.", Type.Object({path, old: Type.String(), replacement: Type.String()})],
    ["run_tests", "Run the visible tests against the current files.", Type.Object({})],
  ] as const;
  for (const [name, description, parameters] of tools) {
    pi.registerTool({name, label: name, description, parameters,
      async execute(_id, args) {
        const result = await call(name, args);
        return {content: [{type:"text", text:JSON.stringify(result)}], details:{}};
      }
    });
  }
  pi.on("before_provider_request", async (event) => {
    const payload = {...event.payload as object, temperature:0, seed:17};
    await call("request", payload);
    return payload;
  });
}
