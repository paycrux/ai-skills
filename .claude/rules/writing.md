# Writing Rules (documents and conversation)

> The canonical version of the `## Communication Style` block that `/task-plan`, `/implement`,
> `/qa-guide`, and `/skill-creator` each carry a one-paragraph summary of. Edit here first.

Applies to prose written for a person to read — plan documents, progress notes, PR bodies, QA
guides, and conversational output. Structured elements (checklists, headers, tables, file paths,
code blocks, figma links) keep their normal format and are not covered here.

## The reader

**Write for someone who has not implemented this feature and does not share your context.**

That reader is real: the person reviewing the PR, the QA engineer running the guide, the teammate
picking up the plan next month, and you three weeks from now. None of them has the code loaded in
their head.

## Rules

**1. Background before conclusion.**
Start from the situation anyone can see, then the choice you made. A sentence that only makes sense
to someone who already read the code is worth nothing to the reader.

**2. Never drop an internal term without unpacking it.**
Serialization formats, protocol details, library internals, framework behavior, in-house
abbreviations. Either spend a sentence on what it is and why it matters here, or leave it out.

**3. When background costs more than two or three sentences, compress the whole point to one line.**
One clear line beats a paragraph the reader skips. This is a real trade — take the line.

**4. No filler.**
전반적으로, ~등을 개선, 안정성 향상, 가독성 향상, 코드 정리, 리팩터링 진행, 로직 수정, 기능 보완.
These add length without information. If deleting the filler leaves nothing, delete the sentence.

**5. State what is, not what was intended.**
Record what the code does and what actually ran. Intent, expected benefit, and effort spent are not
observations — leave them out.

## Failure test

A paragraph a reader can only follow after opening the diff has failed. Delete it, or replace it
with the one line they can follow.
