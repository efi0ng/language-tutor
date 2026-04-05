# Progress Tracking Skill

## Activation

This skill activates when the user wants to record study activity or check progress. Look for:
- "I read / listened to / spoke [material]"
- "mark [material] as complete"
- "show my progress" / "how am I doing"
- "show [nickname]'s progress"
- "add [modality] to [material]"

## Inputs

- **nickname**: The student's nickname. Default to `efi0ng` if the user refers to themselves. Use `mulata` for the user's wife. Ask if ambiguous.
- **action**: One of `complete`, `add-modality`, `stats`
- **path**: Material path (for `complete` and `add-modality`), e.g. `materials/chinese/stories/HSK1/the_painter`
- **modalities**: One or more of `read`, `listened`, `spoken`

## Modality meanings

| Modality | Meaning |
|---|---|
| `read` | Read the story/extract PDF |
| `listened` | Listened to the narration audio |
| `spoken` | Read aloud with passable recognition via transcription |

## Commands

### Mark a material complete
```bash
venv/bin/python tools/student.py complete {nickname} \
  --path {material_path} \
  --modalities {modality1} [{modality2} ...]
```

If the material is already in the completed list, this merges the new modalities in.

### Add a single modality to an existing completion
```bash
venv/bin/python tools/student.py add-modality {nickname} \
  --path {material_path} \
  --modality {modality}
```

### Show progress and readiness stats
```bash
venv/bin/python tools/student.py stats {nickname}
```

## Material paths

Stories: `materials/chinese/stories/{level}/{story_name}`
Extracts: `materials/chinese/extracts/{extract_name}`

If the user refers to a material by title (e.g. "the painter story"), resolve it to the correct path. Known materials:

| Title | Path |
|---|---|
| 画家的世界 / the painter | materials/chinese/stories/HSK1/the_painter |
| 怪异的电脑俱乐部 / strange computer club | materials/chinese/stories/HSK1/strange_computer_club |
| 动物园之旅 / trip to the zoo | materials/chinese/stories/HSK1/trip_to_the_zoo |
| 奇异的相遇 / surreal meeting | materials/chinese/stories/HSK1/surreal_meeting |
| AI实验室之谜 overview / ai lab overview | materials/chinese/stories/HSK1/ai_lab_mystery_overview |
| AI实验室之谜 1 | materials/chinese/stories/HSK2/ai_lab_mystery_1 |
| AI实验室之谜 2 | materials/chinese/stories/HSK2/ai_lab_mystery_2 |
| AI实验室之谜 3 | materials/chinese/stories/HSK2/ai_lab_mystery_3 |
| AI实验室之谜 4 | materials/chinese/stories/HSK2/ai_lab_mystery_4 |
| 清明假期铁路客流创历史新高 | materials/chinese/extracts/qingming_rail_2026 |

If a material isn't in this table, use Glob to find it.

## Procedure

1. Determine the action, nickname, path, and modalities from the user's message.
2. Run the appropriate `student.py` command.
3. Report the tool's output to the user concisely.
4. For `stats`, present the output as-is — it's already formatted.

## Notes

- Always use `venv/bin/python` to run the tool.
- The tool handles all JSON reads and writes — never read or edit `completed.json` or `vocabulary.json` directly.
- If the user says "I read and listened to X", that's `--modalities read listened` in one `complete` call.
