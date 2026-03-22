# Karaoke Video Generation Skill

## Activation

This skill activates when the user asks to generate a karaoke video, karaoke-style video, or synced text video for a language learning story. It also activates when the user asks to create a story AND a karaoke video in the same request.

## Two modes

### Mode A — Existing story
The user points to (or describes) a story that already exists on disk. Generate only the karaoke video for it.

Example prompts:
- "make a karaoke video for the surreal_meeting story"
- "generate karaoke for materials/chinese/stories/HSK1/surreal_meeting"
- "add a karaoke video to the cat story"

### Mode B — Story + karaoke (chained)
The user asks for a new story and a karaoke video in the same breath, or asks you to create a story and then run karaoke on it.

Example prompts:
- "create an HSK1 Chinese story about a dog and also make a karaoke video"
- "write a new story and generate karaoke for it"
- "use the story skill then generate karaoke"

In this mode: **first execute the full story generation skill** (as described in `.claude/skills/story/SKILL.md`), then proceed with karaoke generation below using the story you just created.

## Inputs

- **story_dir**: Path to the story directory, e.g. `materials/chinese/stories/HSK1/surreal_meeting`. Derive this from context:
  - If the user gives an explicit path, use it.
  - If the user gives language + level + story name, construct the path.
  - In chained mode, use the directory just created by the story skill.
- **lang**: The TTS language code for the story (e.g. `zh-CN`, `en-US`, `fr-FR`, `ja-JP`). Derive from context or the story skill's language mapping. The tool uses this to configure Whisper and select character-level (CJK) vs word-level (Latin) highlighting.
- **whisper_model** (optional): `tiny`, `base`, or `small`. Default: `small`. Use `tiny` for a quick preview; use `base` if the user wants a faster run at slightly lower accuracy.

## Procedure

1. **Resolve the story directory** using the inputs above. Verify that `{story_dir}/story.md` and `{story_dir}/narration.mp3` both exist. If either is missing, stop and tell the user.

2. **Run the karaoke tool**:
   ```bash
   venv/bin/python tools/karaoke.py \
     --story {story_dir}/story.md \
     --audio {story_dir}/narration.mp3 \
     --output {story_dir}/karaoke.mp4 \
     --lang {lang} \
     --model {whisper_model}
   ```
   This takes 20–60 seconds depending on story length and model.

3. **Report** to the user:
   - Path to the generated `karaoke.mp4`
   - Audio duration and number of tokens aligned (visible in the tool's stdout)
   - Any warnings (e.g. Whisper alignment gaps)

## What the video contains

- 1280×720 H.264/AAC video
- Dark navy background, large NotoSansSC font
- Story title displayed at the top
- Full story text displayed on screen; each character/word lights up in gold as it is spoken, previously-spoken text dims to gray
- Smooth vertical scroll to keep the current line centred
- Progress bar at the bottom

## Notes

- The tool downloads the Whisper `base` model (~140 MB) on first run; subsequent runs use the cached model.
- For a quicker preview, pass `--model base` or `--model tiny`.
- The output always goes to `karaoke.mp4` inside the story directory alongside the other materials.
