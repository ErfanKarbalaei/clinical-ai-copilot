/**
 * Structured presentation of an assistant answer (Phase 1 design) — pure
 * front-end typography over the existing plain-text response contract:
 *
 * - short lines ending with ":" render as teal section labels (e.g. «خلاصه:»)
 * - lines starting with "-", "•" or "*" render as clinical bullet rows
 * - everything else renders as a calm paragraph
 *
 * Plain prose (no markers) renders unchanged — nothing is altered or invented.
 */

interface Block {
  kind: "heading" | "para" | "bullets";
  lines: string[];
}

function parseBlocks(content: string): Block[] {
  const blocks: Block[] = [];
  for (const raw of content.split("\n")) {
    const line = raw.trim();
    if (!line) continue;

    const bullet = line.match(/^[-•*–]\s+(.+)$/);
    if (bullet) {
      const last = blocks[blocks.length - 1];
      if (last?.kind === "bullets") last.lines.push(bullet[1]);
      else blocks.push({ kind: "bullets", lines: [bullet[1]] });
      continue;
    }

    const heading = line.match(/^(.{1,40})[:：]\s*$/);
    if (heading && !/[.!?]$/.test(heading[1])) {
      blocks.push({ kind: "heading", lines: [heading[1]] });
      continue;
    }

    blocks.push({ kind: "para", lines: [line] });
  }
  return blocks;
}

export function AnswerText({ content }: { content: string }) {
  const blocks = parseBlocks(content);
  return (
    <div className="space-y-2">
      {blocks.map((block, index) => {
        if (block.kind === "heading") {
          return (
            <p
              key={index}
              className="border-s-2 border-brand ps-2 text-xs leading-5 font-semibold text-brand"
            >
              {block.lines[0]}
            </p>
          );
        }
        if (block.kind === "bullets") {
          return (
            <ul key={index} className="space-y-1.5">
              {block.lines.map((line, lineIndex) => (
                <li
                  key={lineIndex}
                  className="flex items-start gap-2 text-[13px] leading-6"
                >
                  <span
                    aria-hidden="true"
                    className="mt-2 size-1 shrink-0 rounded-full bg-brand"
                  />
                  <span className="min-w-0 flex-1">{line}</span>
                </li>
              ))}
            </ul>
          );
        }
        return (
          <p key={index} className="text-[13px] leading-7">
            {block.lines.join("\n")}
          </p>
        );
      })}
    </div>
  );
}
