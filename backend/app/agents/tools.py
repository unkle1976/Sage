TOOLS = [
    {
        "name": "get_weather_forecast",
        "description": (
            "Get the 7-day weather forecast for the user's location. "
            "Use this when the user asks about weather, watering, or "
            "whether it's a good time to plant."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "check_frost_risk",
        "description": (
            "Check frost risk for the next 72 hours at the user's location. "
            "Use this when advising on tender plants, early/late season planting, "
            "or if the user asks about frost."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_watering_guidance",
        "description": (
            "Check whether the user should water their garden today based on "
            "recent rainfall, forecast, and temperature. Use when the user "
            "asks about watering."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_soil_profile",
        "description": (
            "Get soil type information for the user's location. Use when "
            "advising on planting, soil improvement, or plant selection."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "search_plant_database",
        "description": (
            "Search the plant database by common or botanical name. "
            "Use when the user asks about a specific plant's requirements, "
            "growing info, or companions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Plant name to search for (common or botanical).",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_growing_calendar",
        "description": (
            "Get what should be sown, transplanted, or harvested this month "
            "in the user's region. Use when the user asks what to do now, "
            "what to plant, or for monthly guidance."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "month": {
                    "type": "integer",
                    "description": "Month number (1-12). Defaults to the current month if omitted.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "log_context_event",
        "description": (
            "Log a significant gardening event to the context graph for future "
            "reference. Use when the user reports planting, harvesting, problems, "
            "or other notable events."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_type": {
                    "type": "string",
                    "description": (
                        "Type of event: planting, harvest, problem, treatment, "
                        "observation, advice_given."
                    ),
                },
                "summary": {
                    "type": "string",
                    "description": "Short summary of the event.",
                },
                "detail": {
                    "type": "object",
                    "description": "Additional structured detail about the event.",
                },
            },
            "required": ["event_type", "summary"],
        },
    },
    {
        "name": "manage_growing_plan",
        "description": (
            "Add, check, or list items on the user's seasonal growing plan. "
            "Use when the user mentions wanting to grow something, or to check "
            "what's next on their plan."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "list", "check_timing", "activate", "skip"],
                    "description": "What to do with the growing plan",
                },
                "plant_name": {
                    "type": "string",
                    "description": "Name of the plant (for add/check_timing/activate/skip)",
                },
            },
            "required": ["action"],
        },
    },
    {
        "name": "advance_milestone",
        "description": (
            "Record that a plant has reached the next growth milestone. "
            "Use when the user confirms progress like 'they have sprouted' "
            "or 'I have transplanted them'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "plant_name": {
                    "type": "string",
                    "description": "Name or variety of the plant",
                },
                "user_confirmed": {
                    "type": "boolean",
                    "description": "Whether the user explicitly confirmed this milestone",
                },
                "notes": {
                    "type": "string",
                    "description": "Any details the user shared about the milestone",
                },
            },
            "required": ["plant_name"],
        },
    },
]
