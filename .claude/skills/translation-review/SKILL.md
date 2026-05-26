# Translation Review Skill

## Activation

This skill activates when the user asks to review a student's translation. Look for requests mentioning translation review, translation feedback, or checking a translation.

## Inputs (extract from the user's prompt or conversation)

- **student**: Student nickname (e.g. "efi0ng"). Check `CLAUDE.md` for the student list.
- **language**: The source language being translated from (e.g. "chinese", "french"). Default to the student's primary language if not specified.
- **material_path**: Path to the material relative to `materials/{language}/` (e.g. `stories/HSK1/the_painter`). Infer from context if not given.
- **translation_file**: Path to the student's translation file. Default: `students/{student}/{language}/{material_path}/translation_to_english.md`. Confirm by listing the student's folder if uncertain.
- **target_language**: Language the student translated into. Default: English.

## Locating files

Before starting the analysis, read these files:

1. **Source text**: `materials/{language}/{material_path}/story.md` (or `extract.md` for extracts). This is the original text the student translated from.
2. **Reference translation**: `materials/{language}/{material_path}/translation.md` — may or may not exist. If it does, use it as a benchmark. Do not tell the student "the reference says X" — use it silently to inform your analysis.
3. **Student's translation**: the `translation_file` path above.

## Analysis framework

Evaluate the translation across four dimensions. Use these to calculate the scorecard.

### Accuracy (does it convey what the source says?)
- Correct rendering of meaning, including implied meaning
- No omissions of source content
- No additions not in the source
- Word-sense choices that match the specific meaning of the source word (e.g. 安静 = quiet/calm, not peaceful; 不美 = not beautiful, not ugly; 学某人 = to imitate, not to learn about)

### Fluency (does the target text read naturally?)
- Natural sentence rhythm and idiom in the target language
- Appropriate use of connectives (parataxis in Chinese becomes explicit conjunctions in English)
- Colloquialisms not in the source are flagged as style issues

### Mechanics (grammar and spelling)
- Subject-verb agreement
- Pluralisation
- Apostrophes and possessives
- Tense consistency within and across paragraphs
- Typos

### Vocabulary choice (are word choices precise?)
- False cognates or over-literal calques
- Degree of negativity (e.g. 不美 is softer than 丑)
- Register (formal vs. informal)

## Error categories

Tag every issue with one of these four categories:

| Tag | Colour in report | When to use |
|---|---|---|
| **Critical** | Red | Wrong meaning; misread character; omission of content |
| **Minor** | Amber | Imprecise word choice; structural issue; wrong number/tense |
| **Style** | Purple | Additions not in source; naturalness; colloquial flavour |
| **Typo** | Grey | Spelling, punctuation, capitalisation, apostrophes |

## Contrastive analysis — Chinese→English patterns to check

When the source language is Chinese, always check for these common interference patterns:

- **Subject omission**: Chinese allows subjectless clauses; English requires a subject for every finite verb.
- **Pronoun specificity**: 他的 = his (not "this"); 我们的 = our.
- **太阳 vs 阳光**: 太阳 = the sun (object); 阳光 = sunlight/sunshine.
- **水/河/湖**: 水 = water; 河 = river; 湖 = lake. Don't upgrade.
- **安静**: quiet/calm/still — not peaceful (which implies freedom from conflict).
- **不美**: not beautiful — softer than ugly (丑).
- **学某人**: to imitate/copy someone — not "to learn about" someone.
- **但是**: but / however — not nevertheless (which concedes a point).
- **Singular/plural**: Chinese has no mandatory plural marking; watch for 天空 (the sky, singular), 朋友 vs 朋友们, etc.
- **Tense**: Chinese verbs carry no tense inflection. The student must choose; flag inconsistencies.
- **把 sentence structure**: 把X画成Y = paint X into Y. This is handled well when it reads naturally; flag when overly literal.
- **越来越**: more and more — translates well; flag if rendered as a noun phrase.
- **Parataxis**: Chinese chains clauses without conjunctions. English often needs "and", "then", "so", "but".

For other source languages, apply the equivalent contrastive checks appropriate to that language pair.

## Procedure

1. Read the source text, reference translation (if present), and student's translation.
2. Work through the text paragraph by paragraph, identifying all errors and strengths.
3. Categorise every issue (Critical / Minor / Style / Typo).
4. Note standout good choices too — these appear as positive annotations in the report.
5. Calculate the scorecard:
   - **Overall grade**: A/B/C/D based on critical error count and overall accuracy.
   - **Accuracy %**: (sentences with no meaning error / total sentences) × 100, rounded.
   - **Fluency %**: subjective assessment of naturalness, 0–100.
   - **Mechanics %**: (total issues − mechanical issues) / total issues × 100, rounded.
   - **Issue count**: total issues, with breakdown (N critical · N minor · N style/typo).
6. Generate the HTML report (see below).
7. Save the report as `translation_review.html` in the **same directory as the student's translation file**.
8. Report to the user: the file path, the overall grade, and the two or three most important learning points.

## HTML report format

Generate a single self-contained HTML file. Use the full template below as the basis. The report must include:

- **Header** with story name (source language title + English title), student nickname, level, direction, and date.
- **Scorecard** — five metric cells: Overall (letter grade), Accuracy %, Fluency %, Mechanics %, Issues found (count with breakdown).
- **Overview** — 2–3 callout boxes: one green (what the student demonstrated overall), one amber (the most important accuracy issue), one grey (minor patterns to watch).
- **What You Did Well** — bulleted list of genuine strengths with specific examples.
- **Paragraph-by-Paragraph Analysis** — one card per paragraph. Each card contains:
  - The original source text.
  - The student's text with inline `<mark>` highlights (class: `err-crit`, `err-minor`, `err-style`, `err-typo`, `good`).
  - An annotation list: each entry has a `<span class="tag tag-X">` label and an explanation. For critical/minor errors, add a two-column contrast box showing the student's version vs. the better version.
  - For relevant paragraphs, add a "Chinese vs. English structure note" blue callout.
- **Error Summary table** — one row per issue: Type tag | Error description | Fix | Para number.
- **Key Patterns to Watch** — 3–5 named sections, each as a callout box, covering the recurring themes found in this specific translation.
- **Suggested Revision** — pick the paragraph with the most critical errors and show a corrected version in a green callout.
- **Footer** — generation date and framework note.

### CSS and HTML skeleton

Use this exact CSS and structure. Populate `{placeholders}` with the actual content.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Translation Review — {source_title}</title>
<style>
  :root {
    --bg: #fafaf8; --surface: #ffffff; --border: #e5e2da;
    --text: #1a1a18; --muted: #6b6860; --accent: #3d6b8a;
    --accent-light: #e8f1f7; --green: #2d7a4a; --green-light: #e8f5ee;
    --red: #c0392b; --red-light: #fdf0ee; --amber: #b05e00;
    --amber-light: #fdf4e7; --purple: #6b3fa0; --purple-light: #f3eefb;
    --grey: #5a5a58; --grey-light: #f2f2f0;
    --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    --font-mono: "SF Mono", "Fira Code", Consolas, monospace;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: var(--font-sans);
    font-size: 15px; line-height: 1.65; padding: 2rem 1rem; }
  .page { max-width: 860px; margin: 0 auto; }

  header { border-bottom: 2px solid var(--accent); padding-bottom: 1.25rem; margin-bottom: 2rem; }
  header .label { font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase;
    color: var(--accent); font-weight: 600; margin-bottom: 0.4rem; }
  header h1 { font-size: 1.75rem; font-weight: 700; letter-spacing: -0.02em; line-height: 1.2; }
  header .meta { margin-top: 0.6rem; color: var(--muted); font-size: 0.875rem;
    display: flex; gap: 1.5rem; flex-wrap: wrap; }

  .scorecard { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 1rem; margin-bottom: 2rem; }
  .score-cell { background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; padding: 1rem 1rem 0.85rem; }
  .score-cell .label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.07em;
    color: var(--muted); font-weight: 600; margin-bottom: 0.35rem; }
  .score-cell .value { font-size: 1.6rem; font-weight: 700; line-height: 1; }
  .score-cell .sub { font-size: 0.78rem; color: var(--muted); margin-top: 0.2rem; }
  .score-green { border-top: 3px solid var(--green); }
  .score-amber { border-top: 3px solid var(--amber); }
  .score-red   { border-top: 3px solid var(--red); }
  .score-blue  { border-top: 3px solid var(--accent); }
  .score-green .value { color: var(--green); }
  .score-amber .value { color: var(--amber); }
  .score-red   .value { color: var(--red); }
  .score-blue  .value { color: var(--accent); }

  section { margin-bottom: 2.25rem; }
  h2 { font-size: 1.1rem; font-weight: 700; letter-spacing: -0.01em; margin-bottom: 1rem;
    padding-bottom: 0.4rem; border-bottom: 1px solid var(--border); }
  h3 { font-size: 0.95rem; font-weight: 600; color: var(--accent);
    margin-bottom: 0.6rem; margin-top: 1.25rem; }

  .callout { border-radius: 8px; padding: 1rem 1.1rem; margin-bottom: 1rem; font-size: 0.9rem; }
  .callout p { margin-bottom: 0.5rem; }
  .callout p:last-child { margin-bottom: 0; }
  .callout-green  { background: var(--green-light);  border-left: 3px solid var(--green); }
  .callout-amber  { background: var(--amber-light);  border-left: 3px solid var(--amber); }
  .callout-red    { background: var(--red-light);    border-left: 3px solid var(--red); }
  .callout-blue   { background: var(--accent-light); border-left: 3px solid var(--accent); }
  .callout-grey   { background: var(--grey-light);   border-left: 3px solid var(--grey); }
  .callout .tag { display: inline-block; font-size: 0.68rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.07em; border-radius: 3px;
    padding: 0.1em 0.45em; margin-right: 0.4em; vertical-align: middle; }
  .tag-crit  { background: var(--red);    color: #fff; }
  .tag-minor { background: var(--amber);  color: #fff; }
  .tag-style { background: var(--purple); color: #fff; }
  .tag-typo  { background: var(--grey);   color: #fff; }
  .tag-good  { background: var(--green);  color: #fff; }

  .para-card { background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; margin-bottom: 1.5rem; overflow: hidden; }
  .para-card-header { background: var(--grey-light); padding: 0.6rem 1rem;
    font-size: 0.78rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.07em; color: var(--muted); border-bottom: 1px solid var(--border); }
  .para-card-body { padding: 1rem 1.1rem; }

  .source-block { font-size: 0.92rem; margin-bottom: 0.85rem; }
  .source-block .src-label { font-size: 0.68rem; text-transform: uppercase;
    letter-spacing: 0.07em; font-weight: 700; color: var(--muted); margin-bottom: 0.2rem; }
  .zh { font-size: 1rem; line-height: 1.7; color: #3a3a38; }
  .student-text { background: #fffef8; border: 1px solid #e8e5d8; border-radius: 6px;
    padding: 0.75rem 0.9rem; font-size: 0.91rem; line-height: 1.7; margin-bottom: 0.85rem; }

  mark.err-crit  { background: #fde8e8; border-bottom: 2px solid var(--red);    border-radius: 2px; }
  mark.err-minor { background: #fef3e2; border-bottom: 2px solid var(--amber);  border-radius: 2px; }
  mark.err-typo  { background: #f0eff5; border-bottom: 2px solid var(--grey);   border-radius: 2px; }
  mark.err-style { background: #f5f0fc; border-bottom: 2px solid var(--purple); border-radius: 2px; }
  mark.good      { background: #e8f5ee; border-bottom: 2px solid var(--green);  border-radius: 2px; }

  .annotation-list { list-style: none; padding: 0; }
  .annotation-list li { padding: 0.6rem 0; border-bottom: 1px solid var(--border);
    font-size: 0.88rem; display: grid; grid-template-columns: auto 1fr;
    gap: 0.6rem; align-items: baseline; }
  .annotation-list li:last-child { border-bottom: none; }

  .contrast-box { display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem;
    margin-top: 0.6rem; font-size: 0.85rem; }
  .contrast-box .c-col { border-radius: 5px; padding: 0.5rem 0.7rem; }
  .c-student { background: #fdf0ee; }
  .c-better  { background: #e8f5ee; }
  .c-col .c-label { font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.06em; color: var(--muted); margin-bottom: 0.2rem; }

  table { width: 100%; border-collapse: collapse; font-size: 0.87rem; margin-bottom: 1rem; }
  th { text-align: left; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.07em;
    font-weight: 700; color: var(--muted); padding: 0.5rem 0.75rem;
    border-bottom: 2px solid var(--border); background: var(--grey-light); }
  td { padding: 0.6rem 0.75rem; border-bottom: 1px solid var(--border); vertical-align: top; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: #fafaf8; }
  td code { font-family: var(--font-mono); font-size: 0.82rem;
    background: var(--grey-light); padding: 0.1em 0.35em; border-radius: 3px; }

  .strength-list { list-style: none; padding: 0; }
  .strength-list li { display: flex; gap: 0.6rem; align-items: baseline;
    padding: 0.55rem 0; border-bottom: 1px solid var(--border); font-size: 0.9rem; }
  .strength-list li:last-child { border-bottom: none; }
  .check { color: var(--green); font-weight: 700; flex-shrink: 0; }

  footer { margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--border);
    font-size: 0.8rem; color: var(--muted); text-align: center; }

  @media (max-width: 600px) {
    .contrast-box { grid-template-columns: 1fr; }
    .scorecard { grid-template-columns: 1fr 1fr; }
  }
</style>
</head>
<body>
<div class="page">

<header>
  <div class="label">Translation Review</div>
  <h1>{source_title} — {english_title}</h1>
  <div class="meta">
    <span>Student: {student}</span>
    <span>Level: {level}</span>
    <span>Direction: {source_language} → {target_language}</span>
    <span>Date: {date}</span>
  </div>
</header>

<!-- SCORECARD -->
<div class="scorecard">
  <div class="score-cell score-{overall_colour}">
    <div class="label">Overall</div>
    <div class="value">{overall_grade}</div>
    <div class="sub">{overall_subtitle}</div>
  </div>
  <div class="score-cell score-{accuracy_colour}">
    <div class="label">Accuracy</div>
    <div class="value">{accuracy_pct}%</div>
    <div class="sub">{accuracy_subtitle}</div>
  </div>
  <div class="score-cell score-{fluency_colour}">
    <div class="label">Fluency</div>
    <div class="value">{fluency_pct}%</div>
    <div class="sub">{fluency_subtitle}</div>
  </div>
  <div class="score-cell score-{mechanics_colour}">
    <div class="label">Mechanics</div>
    <div class="value">{mechanics_pct}%</div>
    <div class="sub">{mechanics_subtitle}</div>
  </div>
  <div class="score-cell score-blue">
    <div class="label">Issues found</div>
    <div class="value">{total_issues}</div>
    <div class="sub">{critical} critical · {minor} minor · {other} typo/style</div>
  </div>
</div>

<!-- OVERVIEW -->
<section>
  <h2>Overview</h2>
  <div class="callout callout-green"><p>{overall_positive_observation}</p></div>
  <div class="callout callout-amber"><p>{most_important_accuracy_issue}</p></div>
  <div class="callout callout-grey"><p>{minor_patterns_note}</p></div>
</section>

<!-- WHAT YOU DID WELL -->
<section>
  <h2>What You Did Well</h2>
  <ul class="strength-list">
    <!-- one <li> per strength:
    <li><span class="check">✓</span> <span>{strength with specific example}</span></li>
    -->
  </ul>
</section>

<!-- PARAGRAPH-BY-PARAGRAPH -->
<section>
  <h2>Paragraph-by-Paragraph Analysis</h2>

  <!-- Repeat this block for each paragraph: -->
  <div class="para-card">
    <div class="para-card-header">Paragraph {N} — {short description}</div>
    <div class="para-card-body">
      <div class="source-block">
        <div class="src-label">Original ({source_language})</div>
        <div class="zh">{source_paragraph_text}</div>
      </div>
      <div class="student-text">
        {student paragraph with <mark class="err-X"> and <mark class="good"> inline highlights}
      </div>
      <ul class="annotation-list">
        <!-- one <li> per annotation: -->
        <li>
          <span class="tag tag-X">{Type}</span>
          <span><strong>"{highlighted phrase}"</strong> — {explanation with source word in code if helpful}.
            <!-- For critical/minor errors, add a contrast box: -->
            <div class="contrast-box">
              <div class="c-col c-student"><div class="c-label">Your version</div>{student text}</div>
              <div class="c-col c-better"><div class="c-label">Better</div>{improved version}</div>
            </div>
          </span>
        </li>
      </ul>
      <!-- Optional blue callout for a structural note: -->
      <div class="callout callout-blue" style="margin-top:0.75rem; font-size:0.85rem;">
        <p><strong>Structure note:</strong> {contrastive observation}</p>
      </div>
    </div>
  </div>

</section>

<!-- ERROR SUMMARY TABLE -->
<section>
  <h2>Error Summary</h2>
  <table>
    <thead>
      <tr><th>Type</th><th>Error</th><th>Fix</th><th>Para</th></tr>
    </thead>
    <tbody>
      <!-- one <tr> per issue -->
    </tbody>
  </table>
</section>

<!-- KEY PATTERNS -->
<section>
  <h2>Key Patterns to Watch</h2>
  <!-- 3–5 named subsections, each as a callout. Example: -->
  <h3>1. {Pattern name}</h3>
  <div class="callout callout-{colour}"><p>{explanation with vocabulary card if useful}</p></div>
</section>

<!-- SUGGESTED REVISION -->
<section>
  <h2>Suggested Revision (Paragraph {N})</h2>
  <p style="font-size:0.88rem; color: var(--muted); margin-bottom:0.75rem;">
    {Why this paragraph was chosen. One sentence.}
  </p>
  <div class="callout callout-green"><p>{corrected paragraph text}</p></div>
</section>

<footer>
  <p>Translation review generated by Claude Code · Language Tutor project · {date}</p>
  <p style="margin-top:0.3rem;">Framework: MQM-informed rubric with contrastive {source_language}–{target_language} analysis</p>
</footer>

</div>
</body>
</html>
```

## Scorecard colour mapping

| Score | Colour class |
|---|---|
| ≥ 90% / A | `score-green` |
| 75–89% / B | `score-green` or `score-amber` (use green for B+, amber for B/B−) |
| 60–74% / C | `score-amber` |
| < 60% / D | `score-red` |

## Tone and pedagogical approach

- **Lead with strengths**: Always open the "What You Did Well" section with at least three genuine observations, with specific quoted examples. Never invent praise.
- **Explain the why, not just the what**: Every error annotation must explain the linguistic rule or Chinese–English structural difference involved, not just give the correction.
- **Frame errors as patterns**: Group similar mistakes into the "Key Patterns to Watch" section so the student learns a rule, not just a fix.
- **Use metalinguistic labels**: Introduce source-language words in `<code>` tags (e.g. `<code>安静</code>`) to anchor the explanation to the character the student misread or misunderstood.
- **Calibrate the depth**: For HSK 1–2 / beginner materials, focus on character recognition accuracy and basic English grammar. For HSK 3+ / intermediate, emphasise nuance, register, and structural choices.
- **Avoid the word "ugly"** when the source uses 不美 — model the same precision you are teaching.

## Notes

- If no reference translation exists at `materials/{language}/{material_path}/translation.md`, perform the analysis solely against the source text using your own knowledge of the source language.
- The report is purely for the student — do not include information about what Claude did or how the analysis was performed.
- Do not create any temp files; the report is written directly to the output path.
- If the student's translation is in a non-standard location, ask the user for the path before proceeding.
