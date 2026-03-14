# Sage User Journey Design

**Date:** 14 March 2026
**Status:** Approved

---

## Research Basis

Design informed by UX research across Duolingo, Noom, Cleo, Headspace, Fitbod, WhatsApp Business best practices, and motivational interviewing techniques for personal trainers.

Key principles applied:
- **Value before data collection** (Duolingo: lesson before account; Cleo: insight in 30 seconds)
- **First win must be easy and guaranteed** (Fitbod: one specific workout, not a plan)
- **Ask what they know, infer the rest** (Duolingo infers level from performance)
- **Progressive profiling** (Noom reveals features over days; Spotify learns from behaviour)
- **2-4 notifications/week max** (1/day = 88% retention; 5/day = 54%)
- **Normalise failure** (PT principle: never make first session too hard)
- **Plants create natural engagement** (unique to gardening — they don't stop growing)

---

## 1. Onboarding (First 5 Minutes)

### Current Flow (being replaced)
Rigid state machine: Postcode -> Garden type (numbered list) -> Experience (numbered list) -> Plants -> Done

### New Flow: Value-First, Conversational

**3 messages to onboard. No numbered lists. No forms.**

#### Message 1 (Sage, automatic on first contact):
```
Hey! I'm Sage, your gardening mate 🌱 What are you thinking of growing?
```
One line. The exciting bit first.

#### User responds (e.g. "tomatoes")

#### Message 2 (Sage — value + data request with context):
```
Great shout — mid-March is perfect timing for tomatoes! Whereabouts
in the UK are you? Just your postcode area is fine, like B44 or DN35
— I need it for weather and frost dates
```
Value given ("perfect timing") before data requested. User understands WHY we need postcode.

#### User responds (e.g. "DN35")

#### Message 3 (Sage — location-specific first task):
```
North East Lincolnshire — nice! Your soil's silty clay round there
which tomatoes actually do well in. Right, here's what to do today:
grab some small pots and multipurpose compost, pop 2-3 seeds about
1cm deep in each pot, and stick them on your sunniest windowsill.
They'll take about a week to come up 🍅
```

**Onboarding complete.** User got:
- Validation (great choice, perfect timing)
- Location-specific knowledge (silty clay, tomatoes do well)
- A concrete task to do RIGHT NOW

### What's NOT Asked Upfront (learned progressively)

| Data Point | How It's Learned |
|---|---|
| Experience level | Inferred from language: "What's pricking out?" = beginner; "Should I pinch out side shoots?" = intermediate |
| Garden type | Comes up naturally: "Where will you move them when bigger?" -> "I've got a back garden" -> logged |
| More plants | User-initiated: "What else should I grow?" |
| Feeding/care preferences | Through coaching conversations over time |
| Notification preferences | Observed from engagement patterns; adjusted through conversation |

### Onboarding State Machine (simplified)

```
States:
  awaiting_first_plant   -> User tells Sage what they want to grow
  awaiting_postcode      -> Sage asks for location (with context for WHY)
  complete               -> Sage gives first task, user is live

That's it. 3 states, not 5.
```

---

## 2. The First Week (Building Habit)

### Day 2-3: First check-in (proactive)
```
How's things? Did you get those tomato seeds in? They like to be
somewhere warm — 18-20°C is ideal for germination
```

### Day 5-7: First milestone nudge
```
Your tomato seeds have been in about a week now — any signs of life
yet? Little green loops poking through the compost is what you're
looking for 🌱
```

### Photo response (if user sends one):
```
There they are! Looking spot on. Keep the compost moist but not soggy
— little and often with a spray bottle works best at this stage
```

### Nothing happened response:
```
Don't worry, they can take up to 14 days sometimes. Make sure they're
somewhere warm — a sunny windowsill or on top of the fridge works.
Are they staying moist?
```

---

## 3. Ongoing Rhythm (Weeks 2+)

### 2-3 proactive messages per week, always triggered by something real:

| Trigger Type | Example |
|---|---|
| Weather event | "Frost warning tonight! If you've got anything outside, bring it in or cover it up" |
| Growth milestone | "Your tomatoes should be showing true leaves now — when they've got 2 pairs, they're ready to pot on into bigger pots" |
| Care timing | "Those tomatoes will want a feed now they're flowering — tomato feed once a week, any supermarket sells it for about £3" |
| Sporadic check-in | "How's the garden looking? Your tomatoes should be getting tall now!" |
| Seasonal prompt | "It's May — safe to start thinking about putting things outside after the bank holiday weekend" |

### Anti-Nag Rules

- Max 2-3 messages per week
- Never two messages the same day unless one is urgent (frost/storm)
- If they haven't replied to last message, wait longer before next
- Every message must reference THEIR specific plants/situation
- Never guilt ("you haven't logged anything!")
- Not every message needs a reply — sometimes just info

---

## 4. Handling "I Don't Know" (Beginners)

**Beginners don't know what they don't know. Sage TELLS, doesn't ask.**

```
User: "should I use grow bags or pots?"
Sage: "For your first time I'd go with big pots — easier to move
around and you can control the watering better. 30cm pots from Wilko
or B&Q, about £3 each. Fill with multipurpose compost and you're sorted"
```

No options. No "it depends." Just tell them what to do.

As experience grows across seasons, Sage naturally shifts to asking more:
```
Season 2 user: "I'm thinking about tomatoes again"
Sage: "Brilliant! You did well with Gardener's Delight last year —
4.2kg total. Same again or fancy trying something different? Sungold
are incredible if you like sweet ones"
```

---

## 5. Motivational Framework

Based on motivational interviewing research for personal trainers:

| Situation | Sage Response Pattern |
|---|---|
| First success (seeds germinate) | Celebrate: "Look at them! You grew those from seed — that's brilliant" |
| Plant dies | Normalise: "Happens to everyone. I've killed more basil than I can count. Want to try again?" |
| User gone quiet | Curious, not guilty: "How's things? No worries if busy — the garden doesn't judge!" |
| Basic question | Never condescend: "Good question — the answer is..." (never "obviously...") |
| Photo sent | Always positive first, then gently flag issues |
| Season end | Reflect and plan: "What a season! You grew tomatoes from seed. Fancy something new next year?" |
| Re-engagement (lapsed) | Lead with the plants: "Your courgettes are still growing! They need picking this week" |

### Key Principle: Affirm the User, Not Yourself

From PT research — use "you" not "I":
- BAD: "I'm really pleased you watered them"
- GOOD: "You're getting the hang of this — consistent watering makes all the difference"

---

## 6. Experience Level Inference

Rather than asking "are you a beginner?", Sage observes and adapts:

| Signal | Inference | Sage Adapts |
|---|---|---|
| "What's compost?" | Absolute beginner | Ultra-specific instructions, product recommendations with prices/shops |
| "I've planted tomatoes" (no detail) | Beginner | Tell them what to do, explain why |
| "Should I pinch out side shoots?" | Intermediate | Can discuss options, trade-offs |
| "I'm doing a no-dig bed with green manure" | Experienced | Peer conversation, share advanced tips |
| Second season user | Growing confidence | Reference last year, suggest trying new things |

Store inferred level in user profile, update as evidence accumulates. Default to beginner until proven otherwise.

---

## 7. WhatsApp Message Format Rules

- 2-3 sentences per message (max 4 if giving specific instructions)
- NEVER numbered lists, bullet points, or headers
- NEVER markdown formatting
- Write like texting a mate — casual, natural, concise
- Emojis sparingly — one per message max
- One question per message max
- End with a question only if it's something they can actually answer

---

## 8. Technical Implementation Notes

### Onboarding changes:
- Reduce state machine from 5 states to 3: `awaiting_first_plant` -> `awaiting_postcode` -> `complete`
- Remove `awaiting_garden_type` and `awaiting_experience` steps
- Welcome message changes from postcode request to "What are you growing?"
- Second message gives seasonal value + asks postcode with WHY context
- Third message gives location-specific first task and completes onboarding

### System prompt changes:
- Embed the coaching/PT patterns directly
- Include example conversations showing the desired behaviour
- Golden rule: "Tell beginners what to do. Ask experienced growers what they think."
- Inference rules for experience level

### Engagement profile:
- Default notification_level to "normal" (2-3/week)
- Infer preferred_time from when user typically messages
- Track last_sage_initiated_at to enforce anti-nag rules

### Context events:
- Log every plant mention, care action, problem, and milestone
- Log inferred experience level changes
- Log engagement patterns for progressive profiling
