# Storytelling best practices — educational explainer

Each rule has a bad-vs-good example so you can pattern-match against your own draft.

---

## 1. The 5-second hook

Every video opens with a **question the viewer wants answered** or a **counterintuitive observation**. Not a definition. Not a logo. Not "today we'll learn about…".

| Bad | Good |
|---|---|
| "Today, we'll learn about photosynthesis." | "How do leaves *eat sunlight*?" |
| "Welcome back to class six science." | "A plant in a dark closet wilts. Why?" |
| "Photosynthesis is the process by which plants…" | "Why does a plant droop in the dark?" |

A good hook can be tested: can a kid in another room hear ONLY the first 5 seconds and still want to know the answer? If yes, it's working.

## 2. Concrete before abstract

Introduce a phenomenon visually before naming it. The name is the payoff, not the setup.

| Bad | Good |
|---|---|
| "Photosynthesis is when plants use sunlight to make food. Here's how…" | "A plant in a dark closet wilts. A plant in the sun stays green. That difference is photosynthesis." |
| "The mitochondrion is the powerhouse of the cell." | "Some tiny structures inside cells generate all the energy your body uses. Scientists call them mitochondria." |

For class 1–6 especially: **NEVER lead with the term.** Show the thing, then name it.

## 3. One concept per beat

A beat = one idea. If a beat's narration mentions two distinct mechanisms, split it. Animation needs single-focus shots; layered ideas blur visually.

| Bad | Good |
|---|---|
| Single beat: "Sunlight enters the chloroplast, the chlorophyll captures it, and the leaf splits water and pulls CO2 to make glucose." | Beat 3: "Sunlight enters the chloroplast. Chlorophyll captures it." → Beat 4: "With that energy, the leaf splits water and pulls CO2 — building glucose." |
| Single beat: "Newton's first law says objects in motion stay in motion unless acted on, and his second law says force equals mass times acceleration." | One law per beat. Second law has its own setup. |

Rule of thumb: if you'd need two keyframes to describe what the beat shows visually, it's two beats.

## 4. Show, don't define

When the script must define a term, immediately follow with the visual that makes the definition redundant.

| Bad | Good |
|---|---|
| "Chlorophyll is a green pigment in plant cells responsible for photosynthesis." (no visual support — narration carries the whole load) | "Sunlight hits a green pigment called chlorophyll." `<!-- visual: photons entering chloroplast, glowing green pigment grains capturing them -->` |
| "Erosion is the gradual wearing away of land by wind or water." | "Wind and rain slowly carve away the rock. Inch by inch, year by year — that's erosion." `<!-- visual: time-lapse of canyon walls deepening -->` |

If you can describe the visual in one sentence, the narration can be just the name + a connecting phrase. Less narration, more image.

## 5. Recap as payoff, not summary

The recap beat should let the viewer feel they *figured it out*, not be told what they learned.

| Bad | Good |
|---|---|
| "In today's video, we learned that photosynthesis is the process by which plants use sunlight, water, and carbon dioxide to make glucose, releasing oxygen as a byproduct." | "So next time you see a leaf in the sun, you're watching a quiet factory making food — and air for you." |
| "To summarise: Newton's first law, second law, third law…" | "That's why the seat-belt grabs you when the car stops. Newton, alive in every car." |

The recap re-frames the mechanism as something the viewer recognises in their own life. Bad recaps re-state the script; good recaps point to the world.

## 6. Pace per language

Hindi runs ~10% slower than English at the same word count. Devanagari syllables average longer; conjunct consonants need extra time. Size beats accordingly:

| Language | Words per minute (narration) | Notes |
|---|---|---|
| English | ~150 wpm | Standard reference. |
| Hindi (Devanagari) | ~135 wpm | Use Devanagari for numbers and loanwords (`दस` not `10`, `ऑक्सीजन` not `oxygen`). |
| Hinglish | ~140 wpm | When code-switching is intentional. Devanagari Hindi clauses + Latin English clauses. |
| Tamil / Bengali | ~130 wpm | Long native syllables. |
| Spanish | ~160 wpm | Faster than English. |

When in doubt, count the syllables, not the words. Hindi sentences with 8 words might be 22 syllables; English sentences with 8 words might be 12 syllables.

## 7. Tone by class level

| Class | Tone | Vocabulary ceiling | Allowed jargon |
|---|---|---|---|
| 1–3 | warm, exclamatory, lots of "you" | top 1000 words | none unless immediately defined with a visual |
| 4–6 | curious, occasional metaphor | top 3000 words | one technical term per video, defined when introduced |
| 7–9 | precise, occasional jargon with payoff | core academic | technical terms welcome, still pair with visual support |
| 10–12 | expert-friendly, allow technical terms | unrestricted | full technical vocabulary; assume prior exposure |

Class-1 narration sample: *"Look! The plant is sad — its leaves are drooping. Plants are like us — they need food. But plants make their own food!"*

Class-10 narration sample: *"Photosynthesis converts photons into chemical bond energy with about 6% net efficiency. The bottleneck isn't capture — it's RuBisCO's oxygenation side-reaction. Engineering C4 metabolism into C3 crops could lift yields by 30%."*

Same topic, different audience. Pick the right register and hold it.

## 8. The throughline character

When `character_mode != "none"`, a single recurring character in the establishing and closing scenes gives the viewer an emotional anchor — someone to discover the answer alongside.

- The character doesn't have to speak. Reactions carry the throughline.
- Don't introduce more characters in the mechanism beats than you can hold visually consistent — character drift is the dominant Phase 4 failure.
- For multi-character videos (dialogue-driven explainers), introduce all characters in scene 1 and don't add new ones after.

## 9. Avoid stage-direction prose in narration

Narration is what the viewer *hears*. Anything that sounds like a stage direction belongs in the Scene Timeline's Keyframes column or in the `<!-- visual: ... -->` comment, not in narration.

| Bad narration | Good — moved to visual hint |
|---|---|
| "The leaf opens its stomata to take in carbon dioxide, as shown in the diagram." | Narration: *"The leaf pulls in carbon dioxide from the air."* Visual: `<!-- visual: CU on stomata opening, CO2 molecules drifting in -->` |
| "On the right side of the screen, we see the chloroplast." | Visual hint owns the spatial detail. Narration just describes the phenomenon. |

## 10. Numbers and units — speak the way people speak

Children don't naturally say "six point zero two times ten to the twenty-third." Round to memorable forms, then introduce the precise version visually.

| Bad | Good |
|---|---|
| "Each second, the sun emits 3.846 times 10 to the 26 watts of power." | "Every second, the sun pumps out more energy than every machine on Earth could in a year." `<!-- visual: sun → glowing power meter that bursts off the chart -->` |
| "Light travels at 299,792 kilometres per second." | "Light travels nearly 300,000 kilometres in a single second — fast enough to circle the Earth seven times." |

If the precise number matters, show it on screen as an annotation. Narration handles the human-scale framing.
