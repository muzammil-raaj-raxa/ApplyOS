# ApplyOS design system

One visual language for every version. V2 to V4 add pages and items; they do not add new
colors, fonts or motion. Tokens live in frontend/src/styles/tokens.css. Behavior helpers live in
frontend/src/lib/ (format.ts for scores and labels, motion.ts for motion).

## Idea
ApplyOS is an operating system for your job search, not a recruiting site. It is dark, deep
spruce green, lit by two soft pools of light. Chrome stays neutral. Color appears only where it
carries information: how good a match is.

## Color
- Surfaces: spruce-950 (page) to spruce-600. Never pure black.
- Text: pearl (main), mist (supporting), fog (quiet, labels).
- Fit scale, used only for scores: mint 90+, jade 80 to 89, apricot 70 to 79, clay 60 to 69,
  coral under 60. Coral is also the color of errors and rejection. One function decides all of
  this: bandFor() in lib/format.ts.
- Primary actions are pearl-filled. There is no brand accent color on buttons.

## Type
One family, Bricolage Grotesque (bundled, works offline). Its optical size axis opens up small
text and tightens large text. Scale: display (one per page), title, section, heading, lead,
body, label. Numbers use tabular figures so counting never jitters. No uppercase labels, no
monospace: labels are plain sentence case.

## Space and shape
Tailwind's 4px scale. Page gutter and measure are tokens (--gutter, --measure). Data is open
and flat: list rows sit on hairlines, not in cards. Only layers that float above the page are
glass: the dock, the dossier, menus, toasts and the command palette. Controls are soft
rounded rectangles, chips and segments are pills, floating layers have large radii.

## Signature mark: the fit ring
The ring is split into seven arcs, one per scoring dimension. An arc is as long as its weight
in the overall score and as full as the job scored there. At 56px it tells you the grade; at
176px, with the breakdown beside it, it tells you where the grade came from. The Today page
uses the same grammar for the pipeline: concentric rings, each showing what share of the
previous stage survived. Components: FitRing, StageRings (components/viz).

## Motion
Motion answers an action or shows what changed. It never decorates.
- One orchestrated moment: the rings on Today draw in once, from the outside.
- Things you ask for slide in with a spring: the dossier, menus, toasts, the palette.
- The highlight in the dock, segmented controls and the list moves to where you are.
- A score that arrives while you watch draws itself into the ring.
- A hairline at the top of the screen is lit only while the backend is working.
- Pages cross-fade with an 8px lift. Lists do not stagger.
- Prefers-reduced-motion turns numbers and rings static.
Easing: expo-out for entrances. Durations: 140ms, 240ms, 520ms, 950ms for the ring sweep.

## Background
A cool pool of light top-left, a warm one bottom-right, on a fixed layer so it never scrolls
and works on iOS. A very fine grain keeps the gradients from banding.

## Components
Button (primary, secondary, ghost, danger; loading state keeps its width), Segmented, Switch,
TagEditor, Toast, Skeleton, EmptyState, ErrorState, Dock, StatusOrb, CommandPalette, Dossier,
JobRow. All live in frontend/src/components.

## States
- Loading: a shimmer in the exact shape of what is coming.
- Empty: one sentence in large type saying what to do next, with the action beside it.
- Error: what happened, in plain words, and how to fix it (describeError in lib/errors.ts).
- Working: a ring that turns, elapsed seconds on long actions.

## Responsive
The dock becomes a tab bar on phones. The dossier becomes a bottom sheet. Filters scroll
sideways. The Today rings drop below the headline. Touch devices always show row actions.

## Extending it
- New page: add a route in App.tsx and an item in Dock.tsx. Start with one display-size
  headline and the one thing the page is for.
- New number or score: reuse bandFor() for color and AnimatedNumber only for numbers that mean
  something.
- New list: rows on hairlines, actions revealed on hover or focus, a skeleton that matches.
- New action: confirm with a toast that reuses the verb, and offer undo if undo exists.
