"""
Growth milestone timelines and interesting facts for common UK edible plants.

All day counts are from sowing date. Weather gates reflect typical UK conditions
(last frost late April in south, mid-May in north). Milestones use realistic
horticultural data for UK growing seasons.
"""

PLANT_MILESTONES: dict[str, dict] = {
    "tomato": {
        "sow_method": "indoor",
        "milestones": [
            {
                "day": 0,
                "stage": "planted",
                "check_in": "Pop your tomato seeds about 1cm deep in moist compost — a small pot or module tray on a warm windowsill is perfect. They like it around 18-21°C to get going.",
            },
            {
                "day": 10,
                "stage": "germination",
                "check_in": "You should see little green loops pushing through the compost. If nothing yet, give it a few more days — sometimes they take up to 14 days. Keep the compost damp but not soggy.",
            },
            {
                "day": 21,
                "stage": "seedling",
                "check_in": "Your seedlings should have their first pair of true leaves now (the jagged-edged ones, not the smooth seed leaves). If they're looking leggy and stretched, they need more light.",
            },
            {
                "day": 35,
                "stage": "potting_on",
                "check_in": "Time to pot on into individual 9cm pots. Handle them by the leaves, never the stem — a bruised stem won't recover. Bury them a bit deeper than before, tomatoes love that.",
            },
            {
                "day": 60,
                "stage": "hardening_off",
                "check_in": "Start putting them outside during the day and bringing them in at night. Do this for about 10 days to toughen them up. They'll sulk if you skip this step.",
                "weather_gate": {"min_temp": 10, "no_frost": True},
            },
            {
                "day": 70,
                "stage": "transplant",
                "check_in": "Plant them out in their final spot — grow bag, big pot, or border. Plant deep, right up to the first set of leaves. Water well and stake them straight away.",
                "weather_gate": {"min_temp": 12, "no_frost": True},
            },
            {
                "day": 90,
                "stage": "flowering",
                "check_in": "You should see yellow flowers forming in clusters. Give the plant a gentle shake or tap to help pollination. If growing indoors, this is especially important — no bees to do it for you.",
            },
            {
                "day": 110,
                "stage": "fruiting",
                "check_in": "Tiny green tomatoes should be forming where the flowers were. Keep feeding weekly with tomato feed and pinch out any side shoots growing in the leaf joints for cordon varieties.",
            },
            {
                "day": 150,
                "stage": "harvest",
                "check_in": "Your tomatoes should be ripening — look for even colour all over and a slight give when gently squeezed. Pick them regularly to encourage more fruit. Any green ones at the end of the season can ripen on a windowsill next to a banana.",
            },
        ],
        "facts": [
            "Tomatoes are technically berries, and they're in the same family as deadly nightshade — the leaves and stems are mildly toxic.",
            "The UK grows around 400 million tomatoes a year commercially, mostly in heated greenhouses in places like the Isle of Wight and Thanet.",
            "Pinching out side shoots on cordon tomatoes isn't just tidying — it can increase fruit size by up to 30% because the plant puts energy into fewer trusses.",
            "Tomatoes were considered poisonous in Britain until the mid-1700s. People grew them as ornamental plants for decades before anyone dared eat one.",
        ],
    },
    "cucumber": {
        "sow_method": "indoor",
        "milestones": [
            {
                "day": 0,
                "stage": "planted",
                "check_in": "Sow cucumber seeds on their side about 1cm deep in small pots of moist compost. They need warmth — 20°C or above is ideal. A propagator or airing cupboard works well.",
            },
            {
                "day": 7,
                "stage": "germination",
                "check_in": "Cucumber seeds are fast germinators. You should see thick, chunky seedlings pushing through. Move them to a bright windowsill immediately so they don't go leggy.",
            },
            {
                "day": 21,
                "stage": "true_leaves",
                "check_in": "Your plants should have 2-3 true leaves now — they're rough-textured and look nothing like the smooth seed leaves. Keep the compost consistently moist, they hate drying out.",
            },
            {
                "day": 42,
                "stage": "transplant",
                "check_in": "Time to plant out if growing outdoors — into rich soil with plenty of compost dug in. Space them about 45cm apart. For greenhouse cucumbers, a grow bag with 2 plants works well.",
                "weather_gate": {"min_temp": 15, "no_frost": True},
            },
            {
                "day": 56,
                "stage": "training",
                "check_in": "Cucumbers grow fast now — train them up a support or let them sprawl. Pinch out the growing tip of outdoor varieties when they have 6-7 leaves to encourage side shoots where the fruit forms.",
            },
            {
                "day": 70,
                "stage": "flowering",
                "check_in": "Yellow flowers should be appearing. Outdoor varieties need insects for pollination. Greenhouse (all-female) varieties should have male flowers removed — they cause bitter fruit.",
            },
            {
                "day": 85,
                "stage": "harvest",
                "check_in": "Pick cucumbers while they're still smooth and firm — don't let them go yellow and fat. Regular picking keeps new fruit coming. Cut the stem with a knife rather than twisting.",
            },
        ],
        "facts": [
            "The phrase 'cool as a cucumber' is literally true — the inside of a cucumber can be up to 20°C cooler than the outside air temperature.",
            "Cucumbers are 96% water, making them one of the most hydrating foods you can grow.",
            "In the UK, we eat about 130 million cucumbers a year, but most are the long greenhouse type. Outdoor ridge cucumbers have much more flavour.",
        ],
    },
    "lettuce": {
        "sow_method": "either",
        "milestones": [
            {
                "day": 0,
                "stage": "planted",
                "check_in": "Scatter lettuce seeds thinly on the surface of moist compost and press them in gently — they need light to germinate, so don't bury them. Water with a fine rose.",
            },
            {
                "day": 7,
                "stage": "germination",
                "check_in": "Tiny lettuce seedlings should be coming through — they look like little green threads at first. Keep the surface moist with a mister or fine watering. Don't let the compost dry out.",
            },
            {
                "day": 14,
                "stage": "thinning",
                "check_in": "Time to thin your seedlings if they're crowded — aim for about 2-3cm between them. You can eat the thinnings as micro-greens. Use scissors to snip rather than pulling, so you don't disturb the roots of the ones staying.",
            },
            {
                "day": 28,
                "stage": "transplant_or_thin",
                "check_in": "If you started in modules, plant out now with 20-25cm spacing. If sown direct, thin to their final spacing. They look small now but they'll fill out quickly. Water in well.",
            },
            {
                "day": 45,
                "stage": "hearting_up",
                "check_in": "Heading varieties should be starting to form a heart. Loose-leaf types can be harvested now as cut-and-come-again — take outer leaves and leave the centre growing. Keep watered, especially in dry spells.",
            },
            {
                "day": 65,
                "stage": "harvest",
                "check_in": "Lettuces should be ready to harvest. Cut heading types at the base in the morning when they're crispest. Watch for bolting in warm weather — if you see a stem shooting up from the centre, harvest immediately before it turns bitter.",
            },
        ],
        "facts": [
            "Lettuce is a member of the daisy family. If you let it bolt, it produces small yellow flowers that look remarkably like tiny dandelions.",
            "The Romans used to eat lettuce at the end of a meal because they believed it helped them sleep. The milky sap (lactucarium) does actually have mild sedative properties.",
            "You can grow lettuce year-round in the UK with the right varieties — winter-hardy types like 'Winter Density' will crop through even January if given a bit of protection.",
        ],
    },
    "strawberry": {
        "sow_method": "outdoor",
        "milestones": [
            {
                "day": 0,
                "stage": "planted",
                "check_in": "Plant your strawberry plants with the crown (the knobbly bit where the leaves emerge) sitting right at soil level — too deep and they'll rot, too shallow and they'll dry out. Space them 35-40cm apart.",
            },
            {
                "day": 14,
                "stage": "establishing",
                "check_in": "Your strawberry plants should be putting out new light-green leaves from the centre. Water regularly while they establish. If any flower buds appear in the first year, pinch them off — it helps the plant build strength.",
            },
            {
                "day": 30,
                "stage": "growing_on",
                "check_in": "Plants should be producing plenty of new leaves now. Tuck straw or a mulch mat under the leaves to keep fruit clean later and suppress weeds. Watch for slugs — they love strawberries as much as you do.",
            },
            {
                "day": 60,
                "stage": "flowering",
                "check_in": "White flowers with yellow centres should be appearing — each one is a potential strawberry. Bees will do the pollination, so don't spray anything that might put them off. More flowers visited means better-shaped fruit.",
                "weather_gate": {"no_frost": True},
            },
            {
                "day": 80,
                "stage": "fruiting",
                "check_in": "Green fruits are swelling up where the flowers were. Net them now if you don't want the birds eating the lot. Keep watering consistently — irregular watering causes misshapen fruit.",
            },
            {
                "day": 100,
                "stage": "harvest",
                "check_in": "Pick strawberries when they're fully red all over — they don't ripen further once picked. Pick in the morning for best flavour. Eat them the same day for that proper just-picked taste you'll never get from a supermarket.",
            },
        ],
        "facts": [
            "Strawberries are the only fruit with seeds on the outside — each one has about 200 seeds. Technically, each 'seed' is actually a tiny individual fruit called an achene.",
            "The UK strawberry season has been getting longer due to warmer springs. Kent and Herefordshire are the biggest growing regions, producing over 140,000 tonnes a year.",
            "A single strawberry plant can produce up to 500 runners in its lifetime, which is why they take over beds so quickly. Pinch off runners unless you want new plants.",
        ],
    },
    "basil": {
        "sow_method": "indoor",
        "milestones": [
            {
                "day": 0,
                "stage": "planted",
                "check_in": "Scatter basil seeds on the surface of warm, moist compost. Don't cover them — they need light to germinate. Place on the warmest, sunniest windowsill you've got. They want at least 15°C to get going.",
            },
            {
                "day": 10,
                "stage": "germination",
                "check_in": "You should see tiny seedlings with rounded seed leaves. Basil is slow to start — if nothing yet, check the compost is warm enough. Cold windowsills at night are a common killer.",
            },
            {
                "day": 25,
                "stage": "true_leaves",
                "check_in": "First true leaves should be showing — they're the classic basil shape and already smell amazing if you rub them. Thin to the strongest 3-4 seedlings per pot.",
            },
            {
                "day": 42,
                "stage": "pinching_out",
                "check_in": "When plants have 3 pairs of true leaves, pinch out the growing tip. This feels brutal but it's the secret to bushy basil instead of one sad stem. It'll branch out and give you way more leaves.",
            },
            {
                "day": 56,
                "stage": "harvest",
                "check_in": "You can start harvesting regularly now. Always pick from the top, taking whole stem tips rather than individual leaves — this keeps the plant bushy and productive. Don't let it flower if you want the best leaf flavour.",
            },
        ],
        "facts": [
            "Basil is tropical — it's native to India and has been cultivated there for over 5,000 years. That's why it hates UK cold so much and does best on a sunny kitchen windowsill.",
            "Supermarket basil plants are actually dozens of seedlings crammed into one pot, which is why they always die. Thin them out into proper spacing and they'll last for months.",
            "In Italy, putting a pot of basil on your balcony was traditionally a signal that you were ready for a romantic visitor. In the UK, it mainly signals you're making pizza.",
        ],
    },
    "courgette": {
        "sow_method": "indoor",
        "milestones": [
            {
                "day": 0,
                "stage": "planted",
                "check_in": "Push courgette seeds in on their side about 2cm deep — this stops water sitting on the flat surface and rotting them. One seed per 9cm pot of moist compost, somewhere warm (18-21°C).",
            },
            {
                "day": 7,
                "stage": "germination",
                "check_in": "Courgette seeds are strong germinators — you should see a thick stem pushing up and unfurling two big seed leaves. They grow fast from here, so get ready.",
            },
            {
                "day": 21,
                "stage": "true_leaves",
                "check_in": "Large, rough-textured true leaves should be developing. These plants grow quickly and drink a lot — don't let them dry out. Pot on to a 1-litre pot if roots are showing at the bottom.",
            },
            {
                "day": 35,
                "stage": "hardening_off",
                "check_in": "Start hardening off by putting them outside during the day. Courgettes are frost-tender, so bring them in at night until all frost risk has passed. They're big plants — give them room.",
                "weather_gate": {"min_temp": 10, "no_frost": True},
            },
            {
                "day": 42,
                "stage": "transplant",
                "check_in": "Plant out into rich soil — dig in a whole bucket of compost or well-rotted manure per plant. Space at least 90cm apart. They'll look lonely now but in a month they'll be enormous.",
                "weather_gate": {"min_temp": 12, "no_frost": True},
            },
            {
                "day": 56,
                "stage": "flowering",
                "check_in": "Big yellow trumpet flowers should be appearing. Male flowers come first (on thin stalks), females a bit later (with a tiny courgette behind them). If fruits aren't forming, you can hand-pollinate by dabbing a male flower into a female one.",
            },
            {
                "day": 70,
                "stage": "harvest",
                "check_in": "Pick courgettes when they're about 15-20cm long — they taste far better small and firm. Check every other day, because they can go from perfect to marrow-sized in 48 hours. Seriously, don't turn your back on them.",
            },
        ],
        "facts": [
            "A single courgette plant can produce 20-30 fruits in a season, which is why every allotment holder ends up leaving them on neighbours' doorsteps by August.",
            "Courgettes are actually immature marrows — the same plant. The word 'courgette' comes from French, while Americans call them zucchini from the Italian.",
            "The flowers are edible and considered a delicacy. Stuff them with ricotta and herbs, dip in batter, and deep-fry. They're genuinely incredible.",
        ],
    },
    "runner_beans": {
        "sow_method": "outdoor",
        "milestones": [
            {
                "day": 0,
                "stage": "planted",
                "check_in": "Sow runner bean seeds 5cm deep and 15cm apart at the base of your supports — a wigwam of canes or a row of tall stakes. They need something to climb. Water in well.",
                "weather_gate": {"min_temp": 10, "no_frost": True},
            },
            {
                "day": 10,
                "stage": "germination",
                "check_in": "Thick stems should be pushing through the soil. Runner beans are strong — they'll move small stones out of the way. If some seeds haven't come up, pop replacements in now.",
            },
            {
                "day": 21,
                "stage": "climbing",
                "check_in": "Your plants should be reaching for the supports. If they're going the wrong way, gently guide them — runner beans climb anticlockwise (looking from above). Once they find the cane, they'll wind around it on their own.",
            },
            {
                "day": 35,
                "stage": "growing_strong",
                "check_in": "Plants should be climbing well now, with plenty of leaves. Pinch out the growing tip when they reach the top of the supports — this sends energy into flower production instead of more climbing.",
            },
            {
                "day": 49,
                "stage": "flowering",
                "check_in": "Red (or white) flowers should be appearing all the way up the stems. These need bees for pollination. If flowers are dropping without setting pods, try misting them with water — dry conditions stop them setting.",
            },
            {
                "day": 63,
                "stage": "harvest",
                "check_in": "Start picking beans when they're about 15-20cm long and you can't see the bean shapes inside yet. Pick every 2-3 days — once they get stringy and lumpy it's game over for flavour, and the plant stops producing.",
            },
        ],
        "facts": [
            "Runner beans were originally grown as ornamental flowers when they first arrived in the UK from Central America in the 1600s. People thought they were too pretty to eat.",
            "A runner bean plant can grow up to 3 metres tall in a single season — that's about 2-3cm per day in peak growing conditions.",
            "Runner bean roots have nitrogen-fixing nodules, which means they actually improve your soil. After harvesting, cut the plant at ground level and leave the roots in — free fertiliser for next year's crop.",
        ],
    },
    "chilli_pepper": {
        "sow_method": "indoor",
        "milestones": [
            {
                "day": 0,
                "stage": "planted",
                "check_in": "Sow chilli seeds on the surface of moist compost, barely covered. They need real warmth — 25°C is ideal. A heated propagator makes a huge difference. Start early (January-February) because they need a long season.",
            },
            {
                "day": 14,
                "stage": "germination",
                "check_in": "Chilli seeds can be slow and erratic — anywhere from 7 to 21 days. If you see seedlings, brilliant. If not, be patient and keep the compost warm and moist. Don't give up on them.",
            },
            {
                "day": 35,
                "stage": "true_leaves",
                "check_in": "Seedlings should have their first true leaves. They grow slowly at this stage — that's normal. Keep them warm and in the brightest spot you can find. A south-facing windowsill is ideal.",
            },
            {
                "day": 56,
                "stage": "potting_on",
                "check_in": "Pot on into 9cm pots when roots are visible through the drainage holes. Handle seedlings gently — they're delicate at this stage. Keep warm and start feeding with a weak liquid fertiliser fortnightly.",
            },
            {
                "day": 90,
                "stage": "branching",
                "check_in": "Plants should be branching out nicely. When they reach about 20cm tall, pinch out the growing tip to encourage bushier growth and more fruit. Move to their final pot (at least 3 litres for each plant).",
            },
            {
                "day": 120,
                "stage": "flowering",
                "check_in": "Small white flowers should be appearing at the leaf joints. Chillies are self-pollinating, but a gentle shake or tapping the stem helps pollen move. If growing indoors, do this daily.",
                "weather_gate": {"min_temp": 15, "no_frost": True},
            },
            {
                "day": 150,
                "stage": "fruiting",
                "check_in": "Green chillies should be forming and swelling. Keep feeding with tomato feed weekly. They'll stay green for a while — that's fine. Don't overwater now or you'll dilute the heat.",
            },
            {
                "day": 180,
                "stage": "harvest",
                "check_in": "Chillies are ready when they've reached their final colour — usually red, but depends on the variety. You can pick them green for a different (often grassier) flavour. The longer you leave them to ripen, the hotter they generally get.",
            },
        ],
        "facts": [
            "The heat in chillies comes from capsaicin, which the plant evolved to stop mammals eating the fruit. Birds can't taste it at all, which is how the seeds get spread in the wild.",
            "You can overwinter chilli plants in the UK — cut them back hard in autumn, keep them frost-free, and they'll regrow in spring. Second-year plants often crop earlier and heavier.",
            "The world's hottest chillies have been repeatedly bred in the UK. The Carolina Reaper was dethroned by Pepper X at 2.69 million Scoville units — about 500 times hotter than a jalapeño.",
        ],
    },
    "radish": {
        "sow_method": "outdoor",
        "milestones": [
            {
                "day": 0,
                "stage": "planted",
                "check_in": "Sow radish seeds 1cm deep in rows about 15cm apart. Thin them to 2-3cm apart or they'll all elbow each other and you'll get leaves but no radishes. Water the drill before sowing.",
            },
            {
                "day": 5,
                "stage": "germination",
                "check_in": "Radishes are among the fastest germinators in the garden — you should see seedlings within 3-5 days. If they're too crowded, thin now. Use the thinnings in a salad.",
            },
            {
                "day": 12,
                "stage": "swelling",
                "check_in": "You should be able to see the top of the radish root starting to swell at the soil surface. Keep watering consistently — drying out then soaking makes them split or go woody and hot.",
            },
            {
                "day": 18,
                "stage": "nearly_ready",
                "check_in": "Radishes should be looking plump and round at the soil surface. Gently brush the soil away from one to check the size — you want them about 2-3cm across for most varieties.",
            },
            {
                "day": 25,
                "stage": "harvest",
                "check_in": "Pull them up — they should be crisp, peppery, and about the size of a large marble. Don't leave them too long or they go woody and unpleasantly hot. Sow another batch straight away for continuous cropping.",
            },
        ],
        "facts": [
            "Radishes are one of the fastest crops you can grow — some varieties go from seed to plate in just 21 days. They're brilliant for impatient gardeners and great for kids.",
            "The International Space Station has grown radishes as part of plant biology experiments. If they can grow in space, they can definitely grow in your garden.",
            "Radishes are an excellent companion plant — sow them between rows of slow-germinating crops like parsnips. The radishes mark the row and are harvested before the other crops need the space.",
        ],
    },
    "peas": {
        "sow_method": "outdoor",
        "milestones": [
            {
                "day": 0,
                "stage": "planted",
                "check_in": "Sow pea seeds 5cm deep in a flat-bottomed trench about 15cm wide. Space them about 5-7cm apart. A bit of chicken wire over the top stops mice pinching them — they love pea seeds.",
            },
            {
                "day": 10,
                "stage": "germination",
                "check_in": "Pea shoots should be pushing through — they're quite chunky little things. If you notice any gaps where seeds haven't come up, mice probably got them. Fill in with new seeds now.",
            },
            {
                "day": 21,
                "stage": "tendrils",
                "check_in": "Your peas should be putting out curly tendrils, searching for something to grab. Get supports in now — pea netting, twiggy sticks, or anything they can climb. They won't wait for you.",
            },
            {
                "day": 42,
                "stage": "flowering",
                "check_in": "Pretty white or purple flowers (depending on variety) should be appearing. Each flower becomes a pod. Water well from now on — they need moisture to fill the pods properly.",
            },
            {
                "day": 63,
                "stage": "harvest",
                "check_in": "Pick peas when the pods are plump and you can feel the peas inside, but before they get starchy. The sugar starts converting to starch the moment you pick, so eat them as fresh as possible. Nothing from a shop comes close.",
            },
        ],
        "facts": [
            "Peas are one of the oldest cultivated crops — they've been found in 10,000-year-old archaeological sites. The ancient Greeks and Romans grew them, though they ate them dried rather than fresh.",
            "Gregor Mendel used pea plants for his famous genetics experiments in the 1860s. The laws of heredity that underpin modern genetics were discovered through observing pea traits.",
            "Fresh peas contain more vitamin C than most fruits. A handful of raw peas straight from the pod is one of the best snacks in gardening — sweet, crunchy, and full of goodness.",
        ],
    },
    "beetroot": {
        "sow_method": "outdoor",
        "milestones": [
            {
                "day": 0,
                "stage": "planted",
                "check_in": "Sow beetroot seeds 2cm deep in rows 20cm apart. Each 'seed' is actually a cluster of seeds, so you'll get several seedlings from each one. Soak them overnight before sowing to speed up germination.",
            },
            {
                "day": 14,
                "stage": "germination",
                "check_in": "Red-tinged seedlings should be appearing — the colour in the stems is a good sign. Thin clusters to one seedling each, spacing about 10cm apart. The thinnings are edible — tiny beetroot leaves are delicious in salads.",
            },
            {
                "day": 35,
                "stage": "leaf_growth",
                "check_in": "Plants should have several good-sized leaves now. The root is starting to swell underground. Keep watering evenly — irregular watering causes woody rings inside the beetroot.",
            },
            {
                "day": 60,
                "stage": "swelling",
                "check_in": "You should see the tops of beetroot shoulders pushing above the soil surface. They're a beautiful deep red or golden colour depending on variety. Don't earth them up — it's fine for the tops to show.",
            },
            {
                "day": 80,
                "stage": "harvest",
                "check_in": "Harvest when they're about the size of a cricket ball — roughly 5-7cm across. Twist the leaves off rather than cutting to stop them bleeding. Any bigger and they tend to get woody. Baby beets at golf-ball size are sweeter.",
            },
        ],
        "facts": [
            "Beetroot contains betaine, which is used as a natural red food colouring (E162). It's the same compound that turns your wee pink — completely harmless, but it surprises people every time.",
            "During the Napoleonic wars, beet became Europe's main source of sugar when the British naval blockade cut off cane sugar supplies. Sugar beet is still the UK's primary sugar crop today.",
            "Beetroot juice has been shown to improve athletic performance by up to 3% because the nitrates help your muscles use oxygen more efficiently. Several Olympic athletes drink it before events.",
        ],
    },
    "rocket": {
        "sow_method": "outdoor",
        "milestones": [
            {
                "day": 0,
                "stage": "planted",
                "check_in": "Scatter rocket seeds thinly in rows or broadcast over a patch, barely covering them — about 0.5cm deep. They germinate fast in cool, moist conditions. Can be sown from March to September.",
            },
            {
                "day": 5,
                "stage": "germination",
                "check_in": "Rocket is another quick one — seedlings should appear within 4-7 days. They're small at first with rounded seed leaves. Keep the soil moist and watch for flea beetle — tiny holes in the leaves are the giveaway.",
            },
            {
                "day": 14,
                "stage": "true_leaves",
                "check_in": "The true, lobed rocket leaves are developing. These already have that peppery bite. Thin to about 10-15cm apart if growing full-sized plants, or leave closer for baby-leaf harvesting.",
            },
            {
                "day": 28,
                "stage": "harvest",
                "check_in": "You can start picking outer leaves as cut-and-come-again — just take what you need and let the centre keep growing. The younger leaves are milder; older ones pack more of a peppery punch. Harvest before it flowers for best flavour.",
            },
            {
                "day": 42,
                "stage": "succession_sow",
                "check_in": "Your first batch may be bolting (sending up flower stems) especially in warm weather. Sow another batch now for continuous supply. Bolted rocket is bitter, but the flowers are edible and look great in salads.",
            },
        ],
        "facts": [
            "Rocket (or 'arugula' if you're American) was considered an aphrodisiac in ancient Rome. It was often grown near statues of Priapus, the god of fertility.",
            "Wild rocket and salad rocket are actually different species. Wild rocket has narrower, more deeply lobed leaves and is slower growing but more intensely flavoured and perennial.",
            "Rocket is part of the brassica family, along with cabbage and broccoli. That peppery, mustard-like heat comes from the same glucosinolate compounds that make wasabi hot.",
        ],
    },
    "spring_onion": {
        "sow_method": "outdoor",
        "milestones": [
            {
                "day": 0,
                "stage": "planted",
                "check_in": "Sow spring onion seeds 1cm deep in rows 10cm apart. They're tiny seeds, so sow thinly — but don't worry too much about spacing. You can sow every few weeks from March to July for a continuous supply.",
            },
            {
                "day": 14,
                "stage": "germination",
                "check_in": "Thin, grass-like shoots should be coming through. They look fragile but they're tougher than they appear. Keep the area weed-free — onion seedlings can't compete with weeds at all.",
            },
            {
                "day": 28,
                "stage": "thickening",
                "check_in": "Shoots should be thickening up now and looking more like onions than grass. Thin to about 2cm apart if needed. A light feed with a general fertiliser helps at this stage.",
            },
            {
                "day": 42,
                "stage": "nearly_ready",
                "check_in": "Your spring onions are getting close. You should see white bases forming. You can start pulling individual ones when they're pencil-thick — no need to wait for the whole row.",
            },
            {
                "day": 60,
                "stage": "harvest",
                "check_in": "Pull spring onions as you need them — loosen the soil with a fork first so they come out cleanly. Use them within a few days for the best flavour and crunch. Any left too long will start to bulb up properly.",
            },
        ],
        "facts": [
            "Spring onions aren't baby onions — they're a specific variety bred to be harvested young with long green tops. Leaving them in the ground won't give you a big onion (well, not a good one).",
            "In the UK, we eat more spring onions per capita than almost any other European country, largely thanks to the influence of Chinese and South-East Asian cooking on British food culture.",
            "Spring onions are one of the earliest crops you can harvest in spring — overwintering varieties sown in autumn will give you fresh onions from March, when there's almost nothing else ready.",
        ],
    },
    "mint": {
        "sow_method": "either",
        "milestones": [
            {
                "day": 0,
                "stage": "planted",
                "check_in": "If sowing from seed, scatter on the surface of moist compost — don't cover them. If planting a cutting or division, pot it up in good compost. Either way, ALWAYS grow mint in a pot — it'll take over your entire garden otherwise.",
            },
            {
                "day": 14,
                "stage": "germination",
                "check_in": "If from seed, tiny seedlings should be appearing. Mint from seed is slow to establish. If from a cutting or division, new growth should be visible within a week or two. Keep moist.",
            },
            {
                "day": 28,
                "stage": "establishing",
                "check_in": "Your mint should be putting out proper stems with fragrant leaves now. Pinch out the growing tips to encourage bushy growth rather than one lanky stem. It should smell incredible when you brush past it.",
            },
            {
                "day": 42,
                "stage": "growing_strongly",
                "check_in": "Mint grows fast once it's established — you might be surprised how quickly the pot fills up. Start harvesting regularly, taking stem tips. This keeps it productive and stops it getting woody.",
            },
            {
                "day": 56,
                "stage": "harvest",
                "check_in": "Harvest freely — the more you pick, the more it grows. Cut stems just above a pair of leaves. If it flowers, cut it back hard — the leaves taste less good after flowering. It'll regrow within a couple of weeks.",
            },
        ],
        "facts": [
            "Mint is so vigorous it's considered invasive. Its underground runners (stolons) can spread several metres in a single season. Never plant it directly in a bed unless you want mint forever.",
            "There are over 30 species and hundreds of varieties of mint, from chocolate mint to pineapple mint to Moroccan spearmint. They all cross-pollinate freely, which is why named varieties are grown from cuttings, not seed.",
            "Peppermint oil is one of the UK's oldest herbal remedies — it's been used for digestive complaints since at least the 1700s. A cup of fresh mint tea from your own plant genuinely does settle your stomach.",
        ],
    },
    "parsley": {
        "sow_method": "either",
        "milestones": [
            {
                "day": 0,
                "stage": "planted",
                "check_in": "Sow parsley seeds 1cm deep in moist compost. Here's the thing — parsley is notoriously slow to germinate. Pour boiling water over the drill before sowing to warm the soil, or soak seeds overnight. Then be patient.",
            },
            {
                "day": 21,
                "stage": "germination",
                "check_in": "Parsley takes 2-4 weeks to germinate, so don't panic if nothing's happened yet. The old saying is that parsley seed goes to the devil and back seven times before it grows. Keep the soil moist and wait.",
            },
            {
                "day": 35,
                "stage": "true_leaves",
                "check_in": "You should finally see true parsley leaves — flat-leaf types have smooth, divided leaves; curly types have the classic crinkled look. They're still small but growing more confidently now. Thin to 15-20cm apart.",
            },
            {
                "day": 56,
                "stage": "growing_on",
                "check_in": "Your parsley should be producing plenty of stems and leaves now. You can start light harvesting — take outer stems from the base and let the centre keep growing. Feed fortnightly with a liquid fertiliser.",
            },
            {
                "day": 75,
                "stage": "harvest",
                "check_in": "Parsley should be big enough for regular harvesting. Always cut whole stems from the outside — don't just strip individual leaves. It's biennial, so it'll keep producing into winter and try to flower the following spring.",
            },
        ],
        "facts": [
            "Parsley is biennial, meaning it grows leaves in the first year and flowers in the second. Once it bolts and flowers, the leaves turn bitter. Sow fresh each year for the best crop.",
            "Flat-leaf (Italian) parsley has much stronger flavour than curly parsley. Curly parsley is mainly popular in the UK because of its appearance as a garnish — the Victorians loved it on a plate.",
            "Parsley contains more vitamin C than an orange weight for weight, and more iron than spinach. A tablespoon of fresh parsley gives you over a third of your daily vitamin C needs.",
            "The ancient Greeks associated parsley with death and used it to decorate tombs. They wouldn't eat it, which is ironic given how central it became to Mediterranean cooking.",
        ],
    },
}
