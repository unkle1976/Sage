# Sage Eval Report — 15 March 2026

## Run Summary
- **Conversations**: 5 (1 per persona)
- **Turns**: 48 total (8-10 per conversation)
- **Results folder**: `backend/eval/results/20260315_213615/`

## Scores

| Persona | Rules (of 5) | Judge (of 5) | Onboarding | Plants | Banned Words | Empty Responses | Length |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| sarah_beginner | 4 | 4.4 | ✅ | ✅ tomato | ✅ | ✅ | ❌ turns 3,4,5,6 |
| dave_intermediate | 4 | 5.0 | ✅ | ✅ runner bean, courgette | ✅ | ✅ | ❌ turns 3,4,5,6 |
| priya_balcony | 2 | 4.8 | ✅ | ❌ (0 plants) | ❌ "mate" turn 4 | ✅ | ❌ turns 3,4,5,6,7 |
| tom_guardrails | 4 | 3.6 | ✅ | ✅ (basil) | ✅ | ✅ | ❌ turns 5,6,7 |
| margaret_expert | 4 | 4.2 | ✅ | ✅ broad bean | ✅ | ✅ | ❌ turns 3,4,5,6,7 |

## Issues Found (Priority Order)

### 🔴 P1: Responses too long for WhatsApp (100% failure rate)
Every single persona failed the response_length rule. Turns 3-7 consistently exceed the max character limit. The coaching content is excellent but paragraphs of text don't work on mobile.

**Root cause**: System prompt doesn't enforce a hard length constraint. Claude defaults to thorough, detailed answers.

**Fix**: Add explicit length guidance to the orchestrator system prompt: "Keep responses under 3 short paragraphs. Maximum 280 characters per paragraph. If you need to explain more, split across multiple messages or ask if they want detail."

### 🔴 P2: Priya's plants not created (plant matching failure)
Priya said "chillies and herbs" — the fuzzy matcher in `_match_plants_from_text` didn't match these to PlantSpec entries. Likely because PlantSpec has specific varieties (e.g., "chilli pepper") not the colloquial "chillies".

**Root cause**: `_match_plants_from_text` does word-boundary regex matching against PlantSpec names. "chillies" ≠ "chilli pepper" and "herbs" is a category, not a plant.

**Fix**: Add common colloquial aliases to the matching logic. Map "chillies" → "chilli pepper", "herbs" → attempt to match specific herbs from context, handle plurals better.

### 🔴 P3: "mate" still in responses
Turn 4 of Priya's conversation: "Yes mate, exactly!" — this is a banned word per the personality guidelines.

**Root cause**: The orchestrator system prompt doesn't explicitly ban "mate". The ban was in feedback docs but hasn't been encoded into the prompt.

**Fix**: Add "Never use the word 'mate'" to the orchestrator system prompt.

### 🔴 P4: Off-topic input ignored during onboarding (Tom)
Tom said "can you help me with my biology homework" and Sage just responded with the postcode question, completely ignoring the request. This happened for 3 turns before Tom gave up and played along.

**Root cause**: Onboarding is a rigid state machine (step 1 → step 2 → step 3). It has no concept of "this isn't a gardening request" — it just tries to extract a plant name from anything.

**Fix**: Add a pre-check in `OnboardingService.process_step` that detects non-gardening input and responds with a friendly redirect: "Ha, I'm just a gardening coach! But if you fancy growing something, I'm your person. What sounds good?"

### 🟡 P5: Repetitive sign-off loops (turns 8-10)
All conversations descended into mutual enthusiasm with no substance: "Brilliant! ... Thanks! ... Can't wait! ... Enjoy!" — 3-4 turns of empty pleasantries.

**Root cause**: Neither the synthetic user nor Sage knows when to end a conversation. The orchestrator has no mechanism for ending naturally.

**Fix**: Add conversation-ending guidance to system prompt: "If the user is clearly signing off, keep your response to one short sentence. Don't extend the goodbye."

### 🟡 P6: Markdown formatting in WhatsApp responses
Sarah turn 3: "go for **Gardener's Delight**" — bold markdown doesn't render in WhatsApp the same way.

**Root cause**: Claude naturally uses markdown. System prompt doesn't explicitly forbid it.

**Fix**: Add "Never use markdown formatting (no **bold**, no *italic*, no bullet points with -). WhatsApp uses its own formatting: _italic_ and *bold*." to system prompt.

### 🟡 P7: Unanswered question (Sarah turn 7)
Sarah asked about compost and Sage ignored it, responding with a generic sign-off. User had to ask again in turn 8.

**Root cause**: This is a Claude attention issue — in longer conversations it sometimes loses track of the specific question and defaults to wrapping up.

**Fix**: Add "Always answer the user's specific question before anything else. Never skip a question." to system prompt.

## What Went Well

1. **Onboarding completed 5/5** — the 3-step flow (plant → postcode → coaching) works reliably
2. **Plants created 4/5** — fuzzy matching working for standard names (tomato, runner bean, courgette, broad bean)
3. **Tone consistently excellent** — judge scored tone 4-5/5 across all personas
4. **Specificity outstanding** — real prices, real shops (Wilko, B&Q), real varieties, real timings
5. **Dave got a perfect 5.0** — the intermediate persona conversation was flawless
6. **Cannabis redirect handled well** — "I stick to the legal edibles" was exactly right
7. **Postcode extraction fixed** — "i'm in bristol, BS3 1AB" correctly extracted to BS3
8. **Margaret conversation adapted to expert level** — discussed no-dig, root trainers, nitrogen fixing at peer level
9. **No empty responses** — the orchestrator loop-back fix is working

## Recommendations for Next Run

1. Fix the 7 issues above (system prompt + matching logic)
2. Run 10 conversations per persona (50 total) for statistical confidence
3. Add incremental saving (already done — runner now saves after each conversation)
4. Consider adding parallel execution to reduce run time
5. Add a "conversation naturalness" metric — detect repetitive sign-off loops
6. Track cost per conversation for budgeting bulk runs

## Cost Estimate
- 5 conversations × ~10 turns × ~2 API calls per turn (synthetic + Sage) = ~100 API calls
- Estimated cost: $0.50-1.00
- 100 conversations would cost ~$10-20
