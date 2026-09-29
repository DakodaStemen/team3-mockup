---
name: Adaptive Degree Pathway Planner
description: CSUSB-web-styled planner where the prerequisite graph and the plan share one left-to-right timeline.
colors:
  csusb-blue: "#0065bd"
  blue-deep: "#004a8a"
  navy: "#003c71"
  blue-tint: "#e6f0fa"
  logo-gray: "#75787b"
  coyote-gold: "#ffc107"
  white: "#ffffff"
  ground: "#f1f1f1"
  surface-2: "#f7f7f7"
  ink: "#2b2b2b"
  text: "#4b4b4b"
  muted: "#676767"
  line: "#dcdcdc"
  line-strong: "#bdbdbd"
  ok: "#1e7b45"
  ok-tint: "#e8f5ed"
  bad: "#b42318"
  bad-tint: "#fdecea"
  warn: "#8a5a00"
  warn-tint: "#fdf5e1"
typography:
  display:
    fontFamily: "Figtree, system-ui, 'Segoe UI', Roboto, sans-serif"
    fontSize: "2.5rem"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "Figtree, system-ui, 'Segoe UI', Roboto, sans-serif"
    fontSize: "1.6rem"
    fontWeight: 700
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Figtree, system-ui, 'Segoe UI', Roboto, sans-serif"
    fontSize: "1.15rem"
    fontWeight: 700
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Figtree, system-ui, 'Segoe UI', Roboto, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Figtree, system-ui, 'Segoe UI', Roboto, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 700
    letterSpacing: "0.07em"
  numeral:
    fontFamily: "Figtree, system-ui, 'Segoe UI', Roboto, sans-serif"
    fontSize: "1.4rem"
    fontWeight: 700
    fontFeature: "tnum"
rounded:
  inner: "4px"
  base: "5px"
  node: "6px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "20px"
  gutter: "24px"
  column-gap: "32px"
  page-bottom: "48px"
components:
  button-primary:
    backgroundColor: "{colors.csusb-blue}"
    textColor: "{colors.white}"
    rounded: "{rounded.base}"
    padding: "0 16px"
    height: "40px"
  button-primary-hover:
    backgroundColor: "{colors.blue-deep}"
  button-ghost:
    backgroundColor: "{colors.white}"
    textColor: "{colors.csusb-blue}"
    rounded: "{rounded.base}"
    padding: "0 16px"
    height: "40px"
  button-ghost-hover:
    backgroundColor: "{colors.csusb-blue}"
    textColor: "{colors.white}"
  button-small:
    rounded: "{rounded.base}"
    padding: "0 12px"
    height: "32px"
  input:
    backgroundColor: "{colors.white}"
    textColor: "{colors.text}"
    rounded: "{rounded.base}"
    padding: "0 12px"
    height: "40px"
  section-nav:
    backgroundColor: "{colors.csusb-blue}"
    textColor: "{colors.white}"
    padding: "8px 24px"
  section-nav-link-active:
    backgroundColor: "{colors.navy}"
    textColor: "{colors.white}"
    rounded: "{rounded.base}"
    padding: "6px 12px"
  sidebar-block:
    backgroundColor: "{colors.ground}"
    rounded: "{rounded.base}"
    padding: "20px"
  term-card:
    backgroundColor: "{colors.white}"
    rounded: "{rounded.base}"
    padding: "14px"
  tag-sample:
    backgroundColor: "{colors.coyote-gold}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "2px 9px"
  map-node:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.node}"
    width: "86px"
    height: "30px"
  map-node-critical:
    backgroundColor: "{colors.csusb-blue}"
    textColor: "{colors.white}"
---

# Design System: Adaptive Degree Pathway Planner

## Overview

**Creative North Star: "The Campus Timetable"**

The planner is dressed as a csusb.edu inner page: a white utility bar with the two-tone CSUSB logo, a blue gradient title banner, a sticky blue section nav with a navy active pill, white content ruled by hairlines, and light-gray sidebar boxes. A student who has used the university site should read it as part of the same campus web, not as a separate startup product. Figtree stands in for the university's licensed Proxima Nova.

Inside that institutional frame, one idea carries the product: the plan and its prerequisite graph share a single timeline. Terms run left to right, every dependency arrow points forward in time, and a what-if visibly pushes courses to the right, leaving dashed ghosts where they used to sit. Color is spent on lines and state, never on decoration: blue means planned and critical, red plus a diagonal hatch means affected, green means done or better, amber means waiting or uncertain.

Density is medium: a working tool read on laptops and projected in class, so headings are large and plain, numerals are tabular, and the what-if result is legible from across a room. Light is the default; dark is an opt-in theme through the top-bar toggle (stored as `adpp-theme`, applied as `html[data-theme=dark]`).

**Key Characteristics:**

- csusb.edu chrome: white top bar, blue gradient banner, blue sticky section nav, #f1f1f1 sidebar boxes.
- Team-supplied CSUSB logo: arc and mountain in CSUSB blue, wordmark in CSUSB gray, never recolored beyond the dark-theme lift.
- One timeline for plan and graph; terms are columns.
- Color on lines and state only; status always paired with text.
- Small, even corners (5px) and hairline borders; soft shadows only on the stats strip and term cards.

## Colors

A cool institutional palette: one CSUSB blue doing nearly all the work over white and warm-neutral grays, with a status trio held for meaning.

### Primary

- **CSUSB Blue** (csusb-blue): primary buttons, links, the section nav bar, planned-node strokes, critical-path fills and edges, the 3px rule under each term heading, the selected tab, the hero graduation value, focus outlines.
- **Deep Campus Blue** (blue-deep): primary-button hover and the dark end of the banner gradient (`linear-gradient(120deg, #0065bd 0%, #0058a6 55%, #004a8a 100%)`).
- **Coyote Navy** (navy): the product name in the top bar, the active section-nav pill, keyboard focus on map nodes.
- **Blue Wash** (blue-tint): hover rows on course lists and tables, the selected tab's count badge.

### Secondary

- **CSUSB Gray** (logo-gray): the logo wordmark only.
- **Coyote Gold** (coyote-gold): the "Sample student · synthetic data" / "Uploaded transcript · not saved" tag (on dark text #3a2a00) and the loading bar under the section nav. Nothing else.
- **Elective Green** (#007934 light, #5fd08f dark; wash #e3f3ea / #123524): CSUSB's green, only for major electives (course code and "Elective" tag) and its legend swatch. Required courses stay ink; the critical path's blue wins over it.
- **Gen Ed Violet** (#5b45b0 light, #b3a3f5 dark; wash #efebfa / #2a2345): general-education slots only (code and "Gen Ed" tag).
- **Once-a-year** badge uses Warn Amber on its wash with a calendar icon ("Fall only" / "Spring only"); on the map, an amber dot on the node's corner. Missing the term costs a year, so it is never fine print.

### Neutral

- **White** (white): page, top bar, cards, inputs.
- **Campus Gray** (ground): sidebar boxes, alternating term bands on the map, neutral count badges.
- **Chalk** (surface-2): completed-course nodes on the map.
- **Ink** (ink): headings, course codes, values.
- **Body Gray** (text): running text.
- **Quiet Gray** (muted): meta text, course titles, labels, map column heads.
- **Hairline** (line) and **Strong Hairline** (line-strong): borders, table rules, section-head rules, default map edges, input strokes.

### Status

- **Done Green** (ok / ok-tint): passed courses, improved results.
- **Affected Red** (bad / bad-tint): affected courses, delayed results, alerts, ghost and move edges. Always with the hatch and the "(affected)" text.
- **Waiting Amber** (warn / warn-tint): offering warnings and discrepancy flags.

### Dark theme

Dark is a remap of the same roles, not a new palette: page #0d1520, ground #131e2b, surface #152233, surface-2 #1a293c, ink #eef2f6, text #d3dae3, muted #9eaab8, line #26374b, line-strong #3a4e66, blue #5aa9f0 (hover #8cc4f6, tint #15314f), navy #0a2540, section nav #0b3a66, text on blue #06182b, banner `linear-gradient(120deg, #0a3563 0%, #082c52 55%, #06213e 100%)`, logo #4a9fe8 / #b3b6ba, ok #4cc47f, bad #ff7b6e, warn #e8b54a with matching deep tints.

### Named Rules

**The Lines-and-State Rule.** Color appears on edges, strokes, and status, not on decorative fills. Aside from the banner, section nav, and critical-path nodes, surfaces stay white or gray.

**The Never-Color-Alone Rule.** Every status color travels with a second cue: "(affected)" text plus the red hatch, a check icon for passed, a dashed outline for ghosts and unplanned courses, a text label on every legend swatch.

**The Gold Is Rare Rule.** Coyote Gold marks synthetic data and loading only.

## Typography

**Display Font:** Figtree (with system-ui, Segoe UI, Roboto, sans-serif), weights 400/500/600/700
**Body Font:** Figtree

**Character:** A single humanist sans in place of csusb.edu's Proxima Nova: friendly, round, institutional. Hierarchy comes from size and weight, not from a second family.

### Hierarchy

- **Display** (700, 2.5rem, 1.15; 1.9rem under 640px): the student's name in the banner, white on blue. One per page.
- **Headline** (700, 1.6rem; 1.3rem under 640px): section headings between hairline rules (Prerequisite map, Pathway), after the site's ruled "Welcome" heading.
- **Title** (700, 1.15rem): sidebar box headings, underlined by a strong hairline. Term headings run at 0.95rem.
- **Body** (400, 16px, 1.5): running text; secondary copy at 0.85–0.9rem; course meta at 0.78rem.
- **Label** (700, 0.75rem, 0.07em, uppercase): stat labels and table column heads only. Map column heads use the same treatment at 11px.
- **Numeral** (700, 1.4rem, tabular): stat values; the hero graduation value at 1.7rem in CSUSB Blue.

### Named Rules

**The Tabular Numbers Rule.** Units, terms, counts, and dates in data use `font-variant-numeric: tabular-nums`.

## Layout

Content sits in a 1440px max-width column with 24px side gutters (16px under 640px); the top bar aligns its content to 1392px. The page stacks: top bar, full-bleed banner, full-bleed sticky section nav (which also carries the planning-aid notice), then a two-column grid of content (fluid) and a 340px sidebar with 32px gaps. Content areas in order: summary (stats, critical path, "Protect these", other pathways, undo/reset), the Plan (one section with a Terms / Prerequisite map switch), then the bottlenecks and data tabs. The sidebar holds only What-if (with its result) and Ask, and is sticky with its own scroll.

At 1080px and below the grid becomes one column with the sidebar moved directly under the summary, so the what-if stays near the top. At 640px and below the stats strip rewraps with the graduation stat on its own full-width row, the banner controls go full width, and the connection status hides.

Term cards sit in one row per academic year (Fall, Winter, Spring, Summer), each season in a fixed column so rows line up; a 4.5rem year label leads each row, and intersession columns are 0.8 the width of regular ones. Completed terms from the student's history come first in the same grid. The map scrolls horizontally inside its section rather than shrinking below legibility. Spacing moves on a 4px base: 4, 8, 12, 16, 20, 24, 32, 48. Anchor jumps use a 64px scroll padding so headings clear the sticky nav.

## Elevation & Depth

Flat with one soft lift. Depth comes from the white-over-gray contrast between content and sidebar boxes and from hairlines; a single diffuse shadow lifts the stats strip and the term cards, echoing the site's quick-link cards.

### Shadow Vocabulary

- **Card lift** (`box-shadow: 0 2px 8px rgb(0 0 0 / .08)`; dark theme `.35`): stats strip and term cards, always with a 1px hairline border.

### Named Rules

**The One Shadow Rule.** There is one shadow value. Sidebar boxes, results, inputs, and the map stay flat.

## Shapes

Small, even corners: 5px on buttons, inputs, cards, boxes, alerts, and nav pills; 4px on inset elements (course rows, inline warnings); 6px on map nodes; full pills on chips, tags, and count badges. Borders are 1px hairlines; the only heavy strokes are the 3px CSUSB Blue rule under term headings and the 3px underline on the selected tab. The diagonal hatch (-45deg, 6px bands) is the shape of "affected" everywhere it appears: course rows, map nodes, legend swatches.

## Components

### Buttons

Solid and plain, like the site's buttons.

- **Shape:** 5px corners, 40px tall, weight 600.
- **Primary:** CSUSB Blue with white text (dark theme: text #06182b); hover Deep Campus Blue. Run what-if, Keep this plan.
- **Ghost:** white with a 1px CSUSB Blue border and blue text; hover fills blue. Discard and secondary actions.
- **Small:** 32px tall, 12px padding, 0.85rem.
- **Disabled:** 45% opacity. Color transitions 0.15s.
- **Icon button (theme toggle):** 40px square, strong-hairline border turning blue on hover, 18px stroked inline SVG sun/moon.

### Chips and Tags

- **History chips** (banner): pill, 14% white on the banner, 0.8rem: terms completed and units earned, transfer credits, in-progress count (dashed white outline).
- **Kind tags** (course rows): 0.68rem bold pill. Elective on Elective Green wash; GE and Free elective on Campus Gray.
- **Risk badge** (course rows): "+N if failed" in Affected Red on its wash; hidden during a what-if preview. **Risk chips** ("Protect these"): white pills with a red-tinted border, bold code, red "+N", and a green "CATCH-UP" mark when a summer/winter term recovers it.
- **Grade chip** (past terms): Done Green on white; Affected Red on its wash for D/F/W/NC/I; Blue on Blue Wash for "in progress".
- **Sample tag:** Coyote Gold pill, 0.75rem bold, dark text.
- **Count badges** (tabs): pill on Campus Gray; blue on Blue Wash when the tab is selected.

### Cards / Containers

- **What-if panel:** white surface, hairline border, 5px radius, 20px padding. The event is a row of pill chips (one selected, filled blue); term and course sit side by side. The result card follows below with a colored left rule (red for a delay, green for none) and a filled delta pill, and scrolls into view when it appears.
- **Result card:** tinted by outcome (Affected Red or Done Green wash with a 35% border of the same hue), 18px 20px padding, rises 4px on entry (0.22s). Head row pairs the event with a bold delta ("+1 term"); a disclosure lists moved courses.
- **Term card:** white, 1px hairline, card lift, 12px 14px padding; heading carries the term and "used / cap" units over a 3px blue rule. Course rows are full-bleed buttons that wash Blue Wash on hover. Engine notes fold into a "N scheduling notes" disclosure.
- **Past term card:** Campus Gray, dashed hairline, no lift; heading carries "Completed" or "In progress" over a strong gray rule; rows are static with grade chips, and a failed attempt later retaken says so.
- **Intersession card:** Surface-2 with a dashed rule under the heading.
- **Transcript report:** Blue Wash block under the stats: what was read, what was not counted, and that nothing is saved.
- **Stats strip:** one white card split by hairlines, 2fr graduation stat then three equal stats; the graduation cell tints red or green with the result.

### Inputs / Fields

- **Style:** 40px, 1px strong hairline, 5px, white, 0.95rem; selects carry a stroked chevron. Hover darkens the stroke to Quiet Gray; focus is the global 2px blue outline at 2px offset. Labels sit above at 0.8rem bold.
- **On the banner:** white fill, no border, dark text.

### Navigation

- **Section nav:** full-bleed CSUSB Blue bar, sticky at top; white 0.92rem semibold links with 5px corners; hover 14% white; active is a navy pill. A 3px gold bar slides along its bottom edge while loading.
- **Tabs:** muted text on a hairline baseline; selected turns blue with a 3px blue underline.

### Prerequisite Map (signature)

A hand-built SVG timeline. Terms are columns (term name and year in uppercase muted labels), alternating columns banded in Campus Gray, and terms with no linked courses shrink to narrow bands. Nodes are 86x30 rounded rects: planned is white with a blue stroke, critical path is solid blue with white text, done is Chalk with a gray stroke, unplanned is dashed gray, affected is the red hatch with a 2px red stroke. Edges are gray 1.3px curves; OR edges dash 4/3; critical edges are 2.2px blue; long edges route through thin reserved lanes so they never pass behind a node. A moved course leaves a dashed red ghost in its old term joined by a dotted red move edge. Hovering or focusing a node lights its whole prerequisite chain and everything it unlocks in blue and dims the rest to 12–20%; click or Enter opens it in the what-if. A legend with text labels sits above the map.

## Do's and Don'ts

### Do

- **Do** keep the csusb.edu frame: white top bar with the logo, blue gradient banner, blue sticky section nav with a navy active pill, gray sidebar boxes.
- **Do** use the team-supplied logo as supplied: arc and mountain in CSUSB Blue, wordmark in CSUSB Gray.
- **Do** place time on the horizontal axis wherever the plan or its dependencies are drawn.
- **Do** pair every status color with text or a pattern (the "(affected)" label and hatch, check icons, dashed outlines).
- **Do** keep corners at 5px and borders at 1px hairlines; pills only for chips, tags, and badges.
- **Do** keep light as the default and ship every new surface in both themes through the existing custom properties.

### Don't

- **Don't** recolor or redraw the CSUSB logo, or set the product name in a second typeface.
- **Don't** fill surfaces with color for decoration; blue belongs to the banner, the nav, actions, and state.
- **Don't** use Coyote Gold for anything but synthetic-data tags and loading.
- **Don't** add a second shadow value or lift the sidebar boxes.
- **Don't** draw the prerequisite graph as a free-floating force layout detached from the terms.
- **Don't** add a kicker or eyebrow line above headings; the h1 stands on its own, as on csusb.edu.
