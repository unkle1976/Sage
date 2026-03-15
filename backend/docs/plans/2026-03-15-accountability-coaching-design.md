# Accountability Coaching & Growing Plan — Design

**Date:** 15 March 2026
**Status:** Implemented (198 tests passing)
**Approach:** Hybrid — plant milestones drive the *what*, existing scheduler drives the *when*

---

## Vision

Sage becomes an accountability partner — like a personal trainer for your garden. Not just advice when you ask, but proactive check-ins that keep you on track, celebrate your wins, and make sure you're planting at the right time.

Inspired by the Ultimate Performance PT model: regular check-ins, honest feedback, positive reinforcement, and adaptive pacing based on how engaged you are.

---

## 1. Plant Growth Milestones

Every plant species gets a **growth timeline** — a series of milestones with expected days from planting. When a user plants something, Sage calculates actual dates and schedules check-ins.

### Example: Ridge Cucumber (indoor sow, March)

| Day | Milestone | Sage says something like... |
|-----|-----------|----------------------------|
| 0 | Planted | *(already handled — user tells Sage)* |
| 7 | Sprouting expected | "Those cucumber seeds should be poking through by now — seeing any green?" |
| 21 | Seedling care | "Your cucumber seedlings should be about 10cm tall. Keep them on the warmest windowsill you've got" |
| 42 | Hardening off window | "Start getting your cucumbers used to outside — pop them out for a few hours on mild days" |
| 56 | Transplant window | "Weather's warming up — your cucumbers are ready to go outside permanently" |
| 70 | Flowering expected | "You should start seeing yellow flowers on your cucumbers soon — that means fruit's coming!" |
| 90 | First harvest | "Check your cucumbers daily now — they go from perfect to marrow-sized surprisingly quick" |

### Data Model

**PlantSpec additions:**

```python
# New JSONB field on PlantSpec
growth_milestones: [
    {"day": 7, "stage": "sprouting", "check_in": "Seeds should be germinating"},
    {"day": 21, "stage": "seedling", "check_in": "Seedlings need light and warmth"},
    {"day": 42, "stage": "hardening_off", "check_in": "Start acclimatising to outdoors",
     "weather_gate": {"min_temp": 10}},  # Won't trigger if too cold
    ...
]
interesting_facts: [
    "Cucumbers are 95% water — that's why they're so thirsty",
    "Ridge cucumbers are hardier than greenhouse varieties and have more flavour",
    ...
]
```

**Plant model additions:**

```python
planting_date: date           # When user said they planted
next_milestone_index: int     # Which milestone is next (0, 1, 2...)
next_milestone_date: date     # Calculated: planting_date + milestone.day
milestone_delayed: bool       # True if weather-gated and waiting
```

### Positive Reinforcement

When the user confirms a milestone ("yeah they've sprouted!"), Sage celebrates genuinely:
- "Brilliant, 12 out of 15 is a great germination rate! You're doing really well"
- "Your first homegrown cucumber! Supermarket ones won't taste the same now"

Not saccharine — just acknowledging the win like a mate would.

---

## 2. Weather-Fused, Location-Specific Check-ins

Milestones set the *what* — the scheduler checks the *reality* before sending.

### How It Works

When a milestone is due, the scheduler:

1. Checks the user's local weather forecast (Open-Meteo + lat/lon — already built)
2. Checks frost risk (already built)
3. Checks recent rainfall (already built)
4. Passes all context to Claude, which generates the actual message

**The milestone is the trigger, but Claude writes the message with real data.**

### Examples

| Milestone | Weather reality | What Sage sends |
|---|---|---|
| Day 42: Hardening off | 15°C, sunny, no frost | "It's gorgeous in Lewisham tomorrow — 15°C and sunny. Perfect day to pop your cucumber seedlings outside for a couple of hours. Bring them back in before evening though, it drops to 6°C overnight" |
| Day 42: Hardening off | 4°C, frost warning | *(milestone delayed)* "Bit too cold to put your cucumbers out this week — frost forecast Wednesday night. Keep them on the windowsill, I'll let you know when it warms up" |
| Day 56: Transplant | Heavy rain forecast | "Your cucumbers are ready to go outside but hold off a day or two — heavy rain coming Thursday. Soggy soil and fresh transplants don't mix. I'll nudge you when it clears" |
| No milestone | 28°C, no rain 5 days | "It's been proper hot in Lewisham this week with no rain — your cucumbers will be thirsty. Give them a good soak this evening, right at the base, not on the leaves" |

### Key Principle

Milestones can be **delayed** by weather. If it's too cold to transplant, Sage doesn't tell you to transplant — it tells you *why* it's waiting and that it's keeping an eye on it. The milestone stays pending until conditions are right.

### Interesting Facts & Tips

When there's no urgent milestone or weather event, Sage shares something genuinely interesting:
- "Fun fact about your cucumbers — they're actually 95% water, which is why they're so thirsty"
- "The ones you're growing will taste completely different to supermarket ones because you'll pick them fresh"

Keeps engagement without nagging.

---

## 3. Engagement Rhythm & Silence Handling

### Message Frequency (Driven by What's Happening)

- **Active growing season (Mar–Sep):** Every 3–5 days on average. More if milestones cluster, less if nothing's happening
- **Quiet season (Oct–Feb):** Weekly or fortnightly. Planning-focused: "Spring's coming — fancy trying anything new this year?"
- **Never more than one message per day.** Everything bundles into a single check-in
- **Morning delivery** (configurable). Gardeners do their pottering in the morning

### When the User Goes Quiet

| Unanswered messages | What changes |
|---|---|
| 1 | Nothing — carry on as usual |
| 2 | Gentle acknowledgement: "Haven't heard from you in a bit — how are those cucumbers getting on?" |
| 3 | Frequency drops to weekly |
| 4+ | Moves to fortnightly. Messages stay valuable but shorter. No guilt |
| User re-engages | Snaps back to normal frequency immediately. "Welcome back! Your cucumbers have probably..." |

### What Sage Never Does

- Never guilt-trips ("You haven't watered in 2 weeks!")
- Never sends empty check-ins with nothing to say
- Never messages during quiet hours
- Never sends more than one message without a reply (no double-texting)

### Positive Reinforcement Triggers

- User confirms a milestone → celebrate genuinely
- User shares a photo description → engage specifically
- User completes a task Sage suggested → acknowledge: "Nice one, that's them sorted"
- First harvest → big moment: "Your first homegrown cucumber! That's a proper milestone"

### EngagementProfile Additions

```python
unanswered_count: int         # Messages sent without a reply
current_frequency: str        # "normal" | "reduced" | "minimal"
last_proactive_at: datetime   # When Sage last initiated contact
```

---

## 4. The Growing Plan — Seasonal Planting Coach

### Concept

Sage doesn't just track what you've planted — it plans your whole season. Early in the year (or at onboarding), Sage asks: **"What are you hoping to grow this year?"**

The user gives a wishlist. Sage builds a **personalised planting calendar** based on:
- Location (frost dates, soil type, climate zone)
- Current date (what's still viable)
- What they've already planted
- Realistic pacing — don't overwhelm a beginner

### The Wishlist Becomes a Queue

| Plant | Optimal sow window | Status | Sage says... |
|---|---|---|---|
| Cherry Tomatoes | Mid-Mar indoor | **Next up** | "Right, let's get your tomatoes started this week" |
| Strawberries | Apr outdoor | **Queued** | "We'll do strawberries in about 3 weeks when it warms up" |
| Basil | Late Apr indoor | **Queued** | "Basil needs warmth — we'll start that late April" |
| Sweetcorn | May outdoor | **Queued** | "Sweetcorn goes straight outside in May, I'll remind you" |
| Pumpkins | ~~Feb indoor~~ | **Too late** | "Honestly, pumpkins needed starting in February. Courgettes are similar but you can still start them now — fancy those?" |

### Key Behaviours

- **Honest about timing.** If they've missed the window, Sage says so directly and suggests an alternative. No false hope — that builds trust.
- **Paced introduction.** One thing at a time, spaced so the user isn't overwhelmed. "Let's get your tomatoes going first, then we'll tackle strawberries in a couple of weeks."
- **Proactive prompts.** When the next plant's window opens, Sage initiates: "Remember those strawberries on your list? Now's the time — I'll walk you through it."
- **Always open.** Users can add anytime: "I just bought some chilli seeds" → Sage adds them, checks timing, slots them in.
- **Adapts to experience.** Beginner gets one thing at a time. Experienced grower who says "just remind me when" gets a lighter touch.

### Conversation Flow

```
User: "I want to grow tomatoes, strawberries, basil and pumpkins"

Sage: "Great list! Let me check the timing for Lewisham...

 ✅ Cherry tomatoes — start indoors this week, perfect timing
 ✅ Strawberries — we'll do those in mid-April
 ✅ Basil — late April, needs warmth
 ❌ Pumpkins — honestly, you've missed the window for this year.
    They needed starting in February. But courgettes are similar
    and you can still sow those in April — fancy trying those?

Let's start with tomatoes. Got any pots and compost?"
```

### Data Model

```python
# New model: GrowingPlanItem
user_id: FK
plant_spec_id: FK              # What they want to grow
status: str                    # "queued" | "ready" | "active" | "too_late" | "skipped"
optimal_sow_start: date        # Calculated from PlantSpec + user location
optimal_sow_end: date          # Last viable date
suggested_alternative_id: FK   # If too_late, what Sage suggested instead
added_at: datetime
activated_at: datetime         # When Sage said "let's do this one"
```

---

## 5. Architecture — How It All Fits Together

### Flow

```
PlantSpec (growth_milestones JSONB)
    ↓ user plants something
Plant record (next_milestone_date, milestone_index)
    ↓ hourly ARQ cron (existing scheduler)
Proactive Scheduler checks:
    1. Any milestones due today?          (NEW)
    2. Any weather alerts?                (EXISTS)
    3. Any watering needed?               (EXISTS)
    4. Interesting tip to share?          (NEW)
    5. User gone quiet — nudge?           (ENHANCED)
    6. Any growing plan items ready?      (NEW)
    ↓ bundles all triggers
Claude generates ONE message with:
    - Real weather data for user's location
    - Milestone context (what stage their plant should be at)
    - User's conversation history (so it sounds like a continuation)
    - Engagement state (unanswered count, tone adjustment)
    ↓
MessageQueue (Redis stream — EXISTS)
    ↓
Slack/WhatsApp sender
    ↓
ConversationMessage stored as role="assistant"
```

### What's New vs What Exists

| Component | Status |
|---|---|
| ARQ worker + cron jobs | ✅ Built |
| Proactive scheduler | ✅ Built, needs milestone trigger logic |
| Engagement service | ✅ Built, needs unanswered-count tracking |
| Alert service (frost, watering, sowing) | ✅ Built |
| MessageQueue (Redis streams) | ✅ Built |
| ProactiveMessageBuilder | ✅ Built, needs milestone context |
| PlantSpec growth_milestones | 🆕 Add JSONB field + seed data |
| Plant next_milestone tracking | 🆕 Add fields to Plant model |
| Unanswered message counter | 🆕 Add to EngagementProfile |
| Slack/WhatsApp outbound sender | 🆕 Consume queue, post via channel API |
| Plant tips/facts | 🆕 Add to PlantSpec |
| GrowingPlanItem model | 🆕 Seasonal planting queue |

### Seven Proactive Message Types

| Type | Trigger | Example |
|---|---|---|
| **Milestone check-in** | Plant hits a growth stage | "Your cucumbers should be sprouting — seeing any green?" |
| **Weather alert** | Frost, heatwave, storm | "Frost forecast tonight in Lewisham — cover your seedlings" |
| **Watering reminder** | No rain + hot temps | "No rain for 5 days and 26°C tomorrow — give everything a good soak tonight" |
| **Task follow-up** | Sage suggested an action | "Did you get that compost dug in? Your cucumbers will thank you" |
| **Positive reinforcement** | User confirms progress | "12 out of 15 sprouted — that's a cracking germination rate" |
| **Interesting fact/tip** | Nothing urgent, keep engagement | "Fun fact: your cucumber flowers only open for one day" |
| **Re-engagement nudge** | 2+ unanswered messages | "Haven't heard from you in a bit — how's the garden looking?" |
| **Growing plan prompt** | Next plant's window opens | "Remember those strawberries on your list? Now's the time" |

### Bundling Rule

If multiple triggers fire on the same day, Claude weaves them into ONE natural message:
> "Your cucumbers should be ready for hardening off, and the weather's perfect for it — 16°C and sunny tomorrow in Lewisham. Also, give your lettuce a water, it's been dry this week."

---

## 6. Behavioural Psychology Framework

Sage's engagement model is grounded in seven established psychological frameworks. This isn't gamification or dark patterns — it's designing an experience that aligns with how human motivation and habit formation actually work.

### 6.1 The Fogg Behavior Model (B = MAP)

**Source:** BJ Fogg, Stanford Persuasive Technology Lab. *Tiny Habits* (2019).

Behaviour occurs when three elements converge simultaneously: **Motivation** (M), **Ability** (A), and a **Prompt** (P). The critical design insight is that increasing Ability (making things easier) is almost always more effective and more sustainable than trying to increase Motivation.

**How Sage applies this:**

| Element | Sage Implementation |
|---|---|
| **Motivation** | Already high — the user chose to grow something. Sage doesn't need to manufacture motivation, it needs to sustain it through visible progress and small wins |
| **Ability** | Sage removes every barrier. "Get multipurpose compost from Wilko, about £3, fill small pots, plant 1cm deep." No decisions left for the user. No Googling required. The behaviour (planting) becomes trivially easy because every variable is resolved |
| **Prompt** | The milestone check-in IS the prompt. It arrives at the biologically right moment, fused with weather reality. "It's 15°C and sunny tomorrow — perfect day to put your cucumbers outside for a couple of hours." The prompt is timely, specific, and actionable |

**Key principle:** Sage never prompts a behaviour without first ensuring the user has both the ability and motivation to do it. Telling someone to transplant when it's 4°C outside fails the Ability test — so Sage delays the prompt until conditions align.

### 6.2 The Hooked Model (Trigger → Action → Variable Reward → Investment)

**Source:** Nir Eyal, *Hooked: How to Build Habit-Forming Products* (2014).

Users pass through four stages repeatedly: an **external trigger** (notification), an **action** (respond to Sage), a **variable reward** (unpredictable but valuable information), and an **investment** (data, plants, history that makes the product more valuable over time). Eventually, external triggers give way to internal triggers — the user thinks about their garden and opens Sage automatically.

**How Sage applies this:**

| Stage | Implementation |
|---|---|
| **Trigger** | External: proactive milestone check-ins via Slack/WhatsApp. Internal (over time): user sees their seedlings and thinks "I should tell Sage they've sprouted" |
| **Action** | Reply to Sage with an update. Minimal effort — a few words. "Yeah they've sprouted!" |
| **Variable Reward** | This is where Sage differentiates. The reward is unpredictable but always valuable: sometimes it's a weather-specific tip ("Heavy rain Thursday, hold off transplanting"), sometimes a celebration ("12 out of 15 is a brilliant germination rate"), sometimes an interesting fact ("Your cucumber flowers only open for one day — bees have to be quick"), sometimes the next step in their growing plan. The user never knows exactly what they'll get, which creates anticipation |
| **Investment** | Every interaction makes Sage smarter about their garden. Plants tracked, milestones logged, preferences learned, growing plan built. The more they invest, the harder it is to leave — Sage knows their soil type, their frost dates, what they planted and when, what worked last year. Starting over with a generic gardening app means losing all of that accumulated knowledge |

**Ethical guardrail:** Variable reward is used to create genuine value, not compulsive checking. Sage never sends empty pings or creates artificial urgency. Every message has substance.

### 6.3 Self-Determination Theory (Autonomy, Competence, Relatedness)

**Source:** Edward Deci & Richard Ryan, University of Rochester. Research spanning 1985–present.

People sustain engagement when three core psychological needs are met: **Autonomy** (I'm choosing this), **Competence** (I'm getting better at this), and **Relatedness** (I belong to something).

**How Sage applies this:**

**Autonomy:**
- The user chooses what to grow. Sage never overrides their preferences — "I want to grow pumpkins" is respected even if timing is wrong (Sage is honest about it, suggests alternatives, but the user decides)
- The growing plan is THEIR plan. Sage coaches, doesn't dictate
- "Fancy trying broad beans?" is an invitation, not an instruction. The user can say no

**Competence:**
- Progressive skill building. Season 1: "Fill pots with compost, plant 1cm deep." Season 2: "You did well with Gardener's Delight last year — Sungold are a step up if you want to try something different." The advice evolves as the user's competence grows
- Milestone celebrations are competence feedback: "12 out of 15 germinated — that's a great rate for a first go." The user sees evidence they're learning
- When things go wrong: "Happens to everyone. Overwatering is the #1 beginner mistake — the fact you spotted the yellowing early is actually good. Here's what to do." Failure is reframed as learning, not incompetence

**Relatedness:**
- Sage itself is the relationship. A consistent, knowledgeable presence that remembers everything. "How are those cucumbers getting on?" feels like someone cares
- Seasonal context creates implicit community: "Loads of people are getting their tomatoes started this week" — you're not alone
- Future feature: sharing harvests, comparing progress with other Sage users. But even without explicit social features, the Sage relationship itself satisfies relatedness

### 6.4 Identity-Based Habits

**Source:** James Clear, *Atomic Habits* (2018). Building on research by Deci, Ryan, and Bandura.

The most powerful driver of lasting behaviour change is not goals or willpower — it's **identity shift**. Each action you perform reinforces the type of person you believe you are. "I'm a person who grows their own food" is more sustainable than "I want to grow some tomatoes."

**How Sage applies this:**

Sage should progressively reinforce the user's identity as a grower:

| Stage | Identity Reinforcement |
|---|---|
| First planting | "You've got your first seeds in — you're officially growing your own" |
| First sprout | "Look at that — you grew those from a seed. That's all you" |
| First harvest | "Your first homegrown cucumber. Supermarket ones will never taste the same now" |
| Second season | "Coming back for round two! What are we growing this year?" |
| Sharing knowledge | "You could probably teach someone else how to grow tomatoes now" |

**Key insight:** Sage never says "good job" (external validation). It says "you grew that" (identity reinforcement). The difference is crucial — one makes the user feel praised, the other makes them feel like a grower.

**Every interaction is a vote for their identity.** Each time they plant, water, check on seedlings, report progress — they're casting a vote for "I am someone who grows food." Sage's role is to make those votes visible and meaningful.

### 6.5 The Zeigarnik Effect (Open Loops)

**Source:** Bluma Zeigarnik (1927). Widely replicated and applied in UX design.

People remember **incomplete tasks** better than completed ones. The brain keeps unfinished business in active working memory, creating a subtle but persistent pull to return and resolve it.

**How Sage applies this:**

Sage naturally creates open loops through the growing process itself:

- "Your seeds should start sprouting in about a week — I'll check in" → the user is now waiting for sprouts. They'll think about it even when they're not in the app
- "We'll start your strawberries in mid-April when it warms up" → queued item, open loop. The user knows something is coming
- "Your cucumbers are nearly ready to go outside — just waiting for this cold snap to pass" → delayed milestone. The user is anticipating

**The growing plan is one big open loop.** "✅ Tomatoes (started) / ⏳ Strawberries (April) / ⏳ Basil (late April)" — three items, only one complete. The incomplete items pull the user back.

**Ethical guardrail:** These open loops are genuine — the plants actually need attention, the strawberries actually should wait until April. Sage doesn't manufacture artificial incompleteness. The biology of growing creates natural open loops that keep users engaged without manipulation.

### 6.6 Loss Aversion & the Endowment Effect

**Source:** Daniel Kahneman & Amos Tversky, *Prospect Theory* (1979). The endowment effect: Kahneman, Knetsch & Thaler (1990).

The pain of losing something is psychologically **twice as powerful** as the pleasure of gaining it. Once people feel they "own" something, they value it far more than they would if they didn't have it yet.

**How Sage applies this:**

Once a user has seedlings growing, they've invested time, effort, and emotional energy. Those seedlings are THEIRS. Sage subtly reinforces ownership:

- "Your cucumber seedlings need you for the next couple of weeks — keep that compost damp" → responsibility, not guilt. The seedlings depend on them
- "You've got 3 plants on the go and your first harvest is 6 weeks away" → showing them what they'd lose by disengaging
- The growing plan itself becomes an owned asset. Leaving Sage means losing their personalised seasonal calendar, their growing history, their accumulated knowledge

**The subscription retention mechanism is built into the biology.** You can't abandon an app that's tracking living things you're emotionally invested in. The endowment effect means users value their Sage account far more than a new user values the prospect of signing up — because their account contains THEIR garden, THEIR history, THEIR plants.

**Ethical guardrail:** Sage never guilt-trips. "Your plants might die if you don't water" is manipulation. "No rain for 5 days and it's been warm — give everything a soak this evening" is helpful. The distinction is critical.

### 6.7 The Peak-End Rule

**Source:** Daniel Kahneman, Barbara Fredrickson, Charles Schreiber, Donald Redelmeier (1993).

People judge an experience based on two moments: the **peak** (most intense point) and the **end** (how it finished). The duration and average quality of the experience barely matter.

**How Sage applies this:**

**Designing peaks:**
- First harvest is the ultimate peak moment. Sage should make this memorable: "Your first homegrown cucumber! You grew that from a tiny seed in a pot on your windowsill. That's genuinely brilliant 🥒"
- First sprout is the first peak. "There they are! Little green shoots. That's the hardest part done — everything from here gets easier"
- Beating a challenge (surviving a frost, recovering from overwatering) is a peak. "They made it through that cold snap — tough little things. Just like their grower"

**Designing endings:**
- End of season isn't a dead end, it's a bridge: "What a first season — you grew cucumbers from seed! Fancy planning what we'll grow next year? You've got the skills now"
- End of a conversation should leave them with something: a tip, a next step, an anticipation. Never end on "OK" or "Got it"
- If a plant dies, the ending matters enormously: "Gutting. But honestly, that's happened to every gardener who ever lived. You know what went wrong now, and next time you'll nail it. Fancy trying again?"

### 6.8 Implementation Intentions (If-Then Planning)

**Source:** Peter Gollwitzer, NYU. Research from 1993–present. Meta-analyses show medium-to-large effect sizes for health behaviour change.

Forming specific plans in the format "When X happens, I will do Y" dramatically increases the probability of following through. Gollwitzer calls this "strategic automaticity" — the deliberate creation of automatic responses to situational cues.

**How Sage applies this:**

Sage naturally creates implementation intentions through its coaching:

- "When you see the first true leaves — the serrated ones, not the smooth seed leaves — that's when you know they're ready to pot on" → situational cue (seeing leaves) linked to action (pot on)
- "When the forecast shows no frost for 2 weeks, that's your signal to plant them outside" → clear trigger linked to clear action
- "Check the compost when you have your morning coffee — if it feels dry an inch down, give them a water" → anchoring the new behaviour to an existing habit

**This is what separates Sage from a gardening website.** A website says "transplant seedlings when frost risk has passed." Sage says "It's looking good from Wednesday — 14°C and no frost in the forecast for Lewisham. That's your window. Pop them in the ground Thursday morning before it gets too hot."

The implementation intention is fully formed: **When** (Thursday morning), **Where** (in the ground), **How** (before it gets too hot). No ambiguity. No decisions. Just do it.

---

## 7. Psychological Anti-Patterns (What Sage Never Does)

These are the dark patterns we deliberately avoid:

| Anti-Pattern | Why It's Harmful | What Sage Does Instead |
|---|---|---|
| **Guilt-tripping** | Creates shame and disengagement. UP never says "you missed a session" — they say "let's get back on it" | "Haven't heard from you — how's the garden looking?" No reference to missed tasks |
| **Artificial urgency** | "Your plants are DYING!" creates anxiety, not engagement | "No rain for 5 days — give them a soak this evening" is factual and helpful |
| **Streak pressure** | Forces daily engagement that doesn't match the biology of growing | Cadence matches plant lifecycle. No streaks. No daily pressure |
| **Withholding value** | Locking essential growing advice behind premium creates resentment | Core coaching is always available. Premium adds depth, not essentials |
| **Social comparison** | "Other users are doing better than you" is toxic | If social features come, they're collaborative (sharing tips) not competitive |
| **Manufactured incompleteness** | Creating fake tasks to trigger Zeigarnik | Every open loop is real — the plants genuinely need the next step |
| **Notification spam** | More notifications ≠ more engagement. It equals uninstalls | One message per day maximum. Zero if there's nothing worth saying |
| **Sycophancy** | "Amazing job!!!" for planting a seed devalues genuine achievements | Calibrated praise. Planting a seed gets a nod. First harvest gets a celebration |

---

## 8. Measuring Psychological Engagement

How we know if the psychology is working:

| Metric | What It Tells Us | Target |
|---|---|---|
| **Response rate to proactive messages** | Are check-ins landing? Do users feel compelled to reply? | >40% response rate |
| **Time to first response** | How quickly do users reply to Sage? Faster = higher engagement | <2 hours median |
| **Unprompted messages** | Users messaging Sage without a prompt = internal triggers forming | >2 per week by month 2 |
| **Growing plan additions** | Users adding new plants = investment escalation working | >1 new plant per month in season |
| **Milestone confirmation rate** | Users reporting progress = accountability loop working | >60% of milestones confirmed |
| **Second season return rate** | Users coming back next year = identity shift successful | >50% return rate |
| **Subscription retention at 90 days** | Paying users still paying after 3 months | >70% |
| **Churn after first harvest** | Do users leave once they've achieved their goal? | <15% post-harvest churn |

---

## 9. Feature Roadmap

Features identified during the accountability coaching design process. Ordered by impact and feasibility.

### 9.1 Companion Planting Intelligence

**Priority:** High — can implement now via system prompt + PlantSpec data

When a user has multiple plants, Sage proactively suggests beneficial pairings and warns about bad neighbours:

- "Your tomatoes and basil are a great combo — basil repels aphids and they grow well together. Plant them close"
- "Keep your runner beans away from your onions — they don't get on"

**Data model:** Add `companions` and `antagonists` JSONB fields to PlantSpec, containing lists of compatible/incompatible plant names. The orchestrator checks these when the user adds a new plant to their garden.

### 9.2 Harvest Logging & Value Tracking

**Priority:** High — strong retention mechanic (identity reinforcement + loss aversion)

When users harvest, Sage asks "How many did you get?" and logs it. End of season, Sage summarises:

- "You grew 23 cucumbers, 4kg of tomatoes, and enough basil to last all summer"
- "That's roughly £45 worth from the supermarket — and yours tasted better"

**Data model:** New `Harvest` model: `plant_id`, `quantity`, `unit` (count/kg/bunches), `harvested_at`. Estimated retail value per plant in PlantSpec.

**Psychology:** This is identity reinforcement (look what you grew), loss aversion (look what you'd lose), and competence feedback (you're getting better) all in one feature.

### 9.3 Glut Advice

**Priority:** Medium — common real-world problem, high engagement moment

"I've got 30 courgettes and I can't eat them fast enough" is a genuinely common situation. Sage helps with preserving, freezing, and giving away — this IS gardening advice, not recipes:

- "Slice them and freeze — they'll keep for months"
- "Make courgette chutney — you'll thank yourself in winter" (preserving is gardening-adjacent)
- "Give them to neighbours. Seriously, everyone's in the same boat with courgettes in August"

**Boundary:** Sage helps with preserving and storage (gardening), not cooking (recipes). "Freeze them sliced" is fine. "Here's a recipe for ratatouille" is not.

### 9.4 Second Season Intelligence

**Priority:** High — this is where the context graph becomes incredibly powerful

For returning users, Sage references what happened last year:

- "Your tomatoes got blight in August last year. This year, try growing them under cover or pick a blight-resistant variety like Crimson Crush"
- "You did really well with lettuce — want to try a different variety this time? Little Gem is a step up from the butterheads you grew"
- "Last year you planted everything in March and ran out of windowsill space. Want to stagger them this time?"

**No new infrastructure needed** — the context graph already stores this. It's about making the system prompt aware of previous seasons and using the data in recommendations.

### 9.5 Photo Recognition (Future)

**Priority:** Medium-High — killer feature but needs multimodal capability

"My plant looks weird" → user sends photo → Sage identifies the problem:

- Pest identification: "That's aphids — spray them off with a hose, they'll be fine"
- Disease identification: "That yellowing pattern looks like blight — here's what to do"
- Growth stage confirmation: "Those are the first true leaves — time to pot them on"
- "Is this ready to pick?" — "Yeah, that cucumber's perfect. Pick it today before it gets too big"

**Implementation:** Requires multimodal API (Claude Vision). WhatsApp supports image messages. Parse image, generate diagnosis, suggest action.

**Safety guardrail:** Sage should always caveat uncertain identifications: "That looks like it could be powdery mildew, but I'm not 100% from the photo. Can you describe it — is it a white dusty coating?"

### 9.6 Equipment & Shopping Lists with Affiliate Links

**Priority:** Medium — revenue opportunity + user convenience

When Sage tells you to do a task, it checks if you have what you need and provides a shopping list:

- "Before you start, you'll need: multipurpose compost (about £4 from Wilko), small 9cm pots (pack of 10 for £2), and your seeds"
- If they say "no, I need pots" → "Here's exactly the ones I'd recommend" + link

**Revenue model:** Affiliate partnerships with UK garden retailers (Wilko, B&Q, Crocus, Thompson & Morgan, Suttons Seeds). Sage recommends specific products with affiliate links. User gets convenience (one-tap purchase), retailer gets qualified traffic, Sage gets commission.

**Ethical guardrail:** Sage only recommends products the user actually needs for their current task. Never upsells. Never recommends expensive options when cheap ones work fine. The recommendation must be genuinely the best option for the user, not the highest commission item.

**Potential partners:**
- Wilko — budget pots, compost, basic tools
- B&Q — larger items, grow bags, raised beds
- Thompson & Morgan / Suttons — seeds, plug plants
- Crocus — premium plants, fruit bushes
- Amazon — convenience fallback

### 9.7 Cost Tracking (Premium Feature)

**Priority:** Low-Medium — nice retention metric, premium tier feature

Track what users spend (seeds, compost, pots, tools, feed) vs the retail value of what they harvest:

- "You've spent £22 so far this season and harvested £68 worth of veg. That's a 3x return"
- End of season: "Your garden saved you £120 vs buying from the supermarket. And it tasted better"

**Psychology:** Proves the subscription pays for itself. Concrete ROI that users can share ("I saved £120 growing my own food"). Combines loss aversion (you'd lose these savings) with identity reinforcement (you're the kind of person who grows their own).

**Premium tier justification:** This is a "nice to have" not a "need to have" — perfect for premium. Free users get the coaching, premium users get the analytics.

### 9.8 Companion Planting Layout Suggestions

**Priority:** Low — builds on companion planting intelligence

When a user has multiple plants, Sage suggests where to put them relative to each other:

- "Put your basil next to the tomatoes — they help each other. Keep the beans at the other end, away from the onions"
- For raised beds or allotments: simple text-based layout suggestions

### 9.9 Crop Rotation (Second Season+)

**Priority:** Low — only relevant for returning users with dedicated beds

"You grew tomatoes in that spot last year — don't plant them there again. Tomatoes, potatoes, and peppers are all in the same family. Put your beans there instead — they'll fix nitrogen in the soil for next year's heavy feeders."

### 9.10 Seed Saving Guide (Experienced Users)

**Priority:** Low — engagement feature for experienced growers

When a user reaches harvest stage: "If you want to save seeds from your best tomato for next year, here's how..." Deepens the investment and creates a multi-year growing narrative.

---

## 10. Revenue Model

### Free Tier
- Full coaching via WhatsApp/Slack
- Milestone tracking and proactive check-ins
- Weather-fused growing advice
- Growing plan (up to 5 active plants)
- Equipment checks and shopping lists

### Premium Tier (£3.99/month or £29.99/year)
- Unlimited plants
- Cost tracking and ROI analytics
- Second season intelligence (year-over-year learning)
- Photo diagnosis
- Priority support

### Affiliate Revenue
- Product recommendations with affiliate links
- Only when the user genuinely needs something
- Commission from UK garden retailers
- Estimated 5-8% commission on garden supplies
- Average basket £15-25 per recommendation

### Revenue Projections (Conservative)
| Metric | Year 1 | Year 2 |
|---|---|---|
| Free users | 5,000 | 25,000 |
| Premium conversion | 8% (400) | 10% (2,500) |
| Annual premium revenue | £12,000 | £75,000 |
| Affiliate revenue per user/year | £5 | £8 |
| Annual affiliate revenue | £25,000 | £200,000 |
| **Total revenue** | **£37,000** | **£275,000** |

---

## References

- Fogg, BJ (2019). *Tiny Habits: The Small Changes That Change Everything*. Houghton Mifflin Harcourt. [behaviormodel.org](https://www.behaviormodel.org/)
- Eyal, Nir (2014). *Hooked: How to Build Habit-Forming Products*. Portfolio. [nirandfar.com](https://www.nirandfar.com/how-to-manufacture-desire/)
- Deci, Edward L. & Ryan, Richard M. (2000). Self-Determination Theory and the Facilitation of Intrinsic Motivation. *American Psychologist*, 55(1), 68–78. [selfdeterminationtheory.org](https://selfdeterminationtheory.org/theory/)
- Clear, James (2018). *Atomic Habits: An Easy & Proven Way to Build Good Habits & Break Bad Ones*. Penguin Random House. [jamesclear.com/identity-based-habits](https://jamesclear.com/identity-based-habits)
- Zeigarnik, Bluma (1927). On finished and unfinished tasks. *Psychologische Forschung*, 9, 1–85.
- Kahneman, Daniel & Tversky, Amos (1979). Prospect Theory: An Analysis of Decision under Risk. *Econometrica*, 47(2), 263–292.
- Kahneman, Daniel; Knetsch, Jack L.; Thaler, Richard H. (1990). Experimental Tests of the Endowment Effect and the Coase Theorem. *Journal of Political Economy*, 98(6), 1325–1348.
- Kahneman, Daniel; Fredrickson, Barbara; Schreiber, Charles; Redelmeier, Donald (1993). When More Pain Is Preferred to Less: Adding a Better End. *Psychological Science*, 4(6), 401–405. [lawsofux.com/peak-end-rule](https://lawsofux.com/peak-end-rule/)
- Gollwitzer, Peter M. (1999). Implementation Intentions: Strong Effects of Simple Plans. *American Psychologist*, 54(7), 493–503.
- Nielsen Norman Group. Autonomy, Relatedness, and Competence in UX Design. [nngroup.com](https://www.nngroup.com/articles/autonomy-relatedness-competence/)
- Interaction Design Foundation. Loss Aversion Theory and the Endowment Effect. [interaction-design.org](https://www.interaction-design.org/literature/article/loss-aversion-theory-the-economics-of-design)
