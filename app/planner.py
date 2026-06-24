"""
planner.py
==========
The four-step itinerary planning chain.
"""

import anthropic
import os
import sys

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096


def get_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n  ANTHROPIC_API_KEY not set.")
        print("  Run: $env:ANTHROPIC_API_KEY = 'your-key-here'")
        sys.exit(1)
    return anthropic.Anthropic(api_key=api_key)


DISCOVER_SYSTEM = """You are a local events researcher. Your job is to find out what is
actually happening at a travel destination during specific dates.

Search for:
- Highland games, agricultural shows, festivals, markets, fairs
- Sporting events, community events, seasonal events
- Museum exhibitions, theatre, concerts, outdoor events
- Anything happening in the destination town AND within a 1hr drive

Search strategy:
- Search "[destination] events [month] [year]"
- Search "[destination] highland games [year]"
- Search "[destination] festival [month] [year]"
- Search "[county/region] events [month] [year]" for nearby events
- Check visitscotland.com and local council event listings if possible

CRITICAL YEAR RULE - apply this before including any event:
- You must confirm the event is running in the exact year of the travel dates
- Search specifically for "[event name] [year]" to confirm the current year edition
- If you cannot find confirmation that the event is running in the correct year, do NOT include it
- A result from a previous year is not confirmation - festivals cancel, change dates, or fold
- If in doubt, exclude - a missing event is better than a wrong one

DATE FILTERING - apply this before including any event:
- Check the event dates against the supplied travel dates
- If the event falls outside the travel window, do NOT include it
- Do not include events that have already passed or not yet been confirmed for the correct dates

Output format - return a structured list:
EVENT FOUND: [name] | [confirmed date] | [location] | [brief description] | [source confirming year]
NO EVENTS FOUND: [what you searched for]
EXCLUDED: [name] | [reason: wrong year / outside travel dates / unconfirmed]

Be thorough - but accurate. A short confirmed list is better than a long unverified one."""


def discover_events(client, trip_brief):
    print("\n Step 0/3 - Discovering local events (web search running)...")

    web_search_tool = {
        "type": "web_search_20250305",
        "name": "web_search",
        "max_uses": 8
    }

    messages = [
        {
            "role": "user",
            "content": f"Search for events happening at this destination during these travel dates:\n\n{trip_brief}"
        }
    ]

    max_iterations = 15
    iteration = 0

    try:
        while iteration < max_iterations:
            iteration += 1

            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=DISCOVER_SYSTEM,
                tools=[web_search_tool],
                messages=messages,
                stop_sequences=None
            )

            print(f"   iteration {iteration}: stop_reason={response.stop_reason}, blocks={len(response.content)}")

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if block.type == "text":
                        print(f"   events discovered: {len(block.text)} chars")
                        print(" Step 0 complete.")
                        return block.text
                print(" Step 0: no text block in end_turn")
                return "No events data returned."

            elif response.stop_reason == "pause_turn":
                messages.append({"role": "assistant", "content": response.content})
                print(f"   searching...")

            else:
                print(f"   unexpected stop_reason: {response.stop_reason}")
                for block in response.content:
                    if hasattr(block, "type") and block.type == "text":
                        return block.text
                break

        print(" Step 0: iteration limit reached")
        return "Event discovery did not complete - proceed without event data."

    except Exception as e:
        print(f" Step 0 FAILED: {type(e).__name__}: {e}")
        print(" Continuing without event data.")
        return "Event discovery failed - proceed without event data."


GENERATE_SYSTEM = """You are an experienced travel planner with deep knowledge of
attractions, cafes, gardens, distilleries, walks, and seasonal access.

Produce a detailed day-by-day draft itinerary from the trip brief and discovered events.

Rules:
- Suggest real, named places only
- For each item note: name, type, why it suits the group
- Flag anything with seasonal restrictions or limited opening hours with [CHECK]
- Keep pace realistic
- Where the brief is vague about preferences (e.g. interest in music, food, art),
  offer a range across 2-3 specific styles or options rather than defaulting to one
- IMPORTANT: Only include events from the events discovery section that are explicitly
  marked EVENT FOUND - do not include anything marked EXCLUDED

Driving radius:
- Primary activities within 30 minutes of base
- One longer drive (up to 1hr-1hr30min) acceptable per trip, not on consecutive days

Wet weather:
- Include a wet weather alternative for each day (indoor or sheltered)
- Label clearly as: WET WEATHER ALTERNATIVE: [option]

Format: structured day-by-day markdown"""


def generate_itinerary(client, trip_brief, events):
    print("\n Step 1/3 - Generating draft itinerary...")

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=GENERATE_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": f"Create a detailed itinerary for this trip.\n\nTRIP BRIEF:\n{trip_brief}\n\nEVENTS DISCOVERED AT DESTINATION:\n{events}"
                }
            ],
            stop_sequences=None
        )

        draft = response.content[0].text
        print(f"   draft: {len(draft)} chars")
        print(" Step 1 complete.")
        return draft

    except Exception as e:
        print(f" Step 1 FAILED: {type(e).__name__}: {e}")
        raise


VERIFY_SYSTEM = """You are a meticulous travel researcher applying Verification Protocol 2.

Take a draft itinerary and verify every date-dependent item against the actual travel
dates using web search.

For EVERY named venue, attraction, walk, cafe, or activity:
1. Search for current opening hours, access restrictions, seasonal closures
2. Check specifically against the travel dates provided
3. Mark each item:
   CHECK_PASS: [venue] - confirmed open/accessible on [dates]
   CHECK_FAIL: [venue] - [reason: closed / outside travel dates / unverified]

CRITICAL REMOVAL RULES - these are not suggestions:
- Any event whose confirmed dates fall outside the travel window: CHECK_FAIL, mark REMOVE
- Any event that cannot be confirmed as running in the correct year: CHECK_FAIL, mark REMOVE
- Any venue confirmed closed during the travel dates: CHECK_FAIL, mark REMOVE
- CHECK_FAIL items marked REMOVE must not appear in the day-by-day itinerary
- They go to the exclusions list only - not flagged inline, not softened, removed entirely

Critical checks:
- Royal estates (Balmoral etc) - check royal residence calendar
- NTS/Historic Environment Scotland properties - check seasonal hours
- Distilleries - check tour booking requirements and opening days
- Cafes/restaurants - check current trading status
- Any item marked [CHECK] in the draft
- Every event in the draft - confirm year and dates explicitly
- Every named venue, restaurant, museum, pub, or attraction - confirm it is currently
  trading. Search "[venue name] [city] closed" and "[venue name] [city] 2026".
  If there is any evidence the venue has closed, relocated, or permanently changed,
  mark CHECK_FAIL and REMOVE - do not include a closed venue as a recommendation

Output format:
1. EXCLUSIONS LIST: items removed and why
2. VERIFICATION SUMMARY: pass/fail count
3. CLEAN ITINERARY: day-by-day with only CHECK_PASS and genuinely uncertain items"""


def verify_itinerary(client, draft, trip_brief):
    print("\n Step 2/3 - Verifying (web searches running)...")

    web_search_tool = {
        "type": "web_search_20250305",
        "name": "web_search",
        "max_uses": 10
    }

    messages = [
        {
            "role": "user",
            "content": f"Trip brief for date context:\n{trip_brief}\n\nDRAFT ITINERARY TO VERIFY:\n{draft}"
        }
    ]

    max_iterations = 15
    iteration = 0

    try:
        while iteration < max_iterations:
            iteration += 1

            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=VERIFY_SYSTEM,
                tools=[web_search_tool],
                messages=messages,
                stop_sequences=None
            )

            print(f"   iteration {iteration}: stop_reason={response.stop_reason}, blocks={len(response.content)}")

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if block.type == "text":
                        print(" Step 2 complete.")
                        return block.text
                return draft

            elif response.stop_reason == "pause_turn":
                messages.append({"role": "assistant", "content": response.content})
                print(f"   searching...")

            else:
                print(f"   unexpected stop_reason: {response.stop_reason}")
                for block in response.content:
                    if hasattr(block, "type") and block.type == "text":
                        return block.text
                break

        print(" Step 2: iteration limit reached")
        return draft

    except Exception as e:
        print(f" Step 2 FAILED: {type(e).__name__}: {e}")
        return draft


FORMAT_SYSTEM = """You are a travel itinerary formatter.

Take a verified itinerary and produce a clean, readable final version.

Format rules:
- Clear day-by-day structure with dates
- Each item: time suggestion, venue name, brief description, status (CONFIRMED / CHECK BEFORE VISITING)
- CHECK BEFORE VISITING items include a one-line note on what to confirm
- Events discovered from Step 0 should be clearly highlighted as KEY EVENT
- End with a Before You Go checklist of all items needing manual confirmation
- Friendly, practical tone

CRITICAL EXCLUSION RULE:
- Any item marked CHECK_FAIL or REMOVE in the verified content must not appear in the
  day-by-day itinerary under any circumstances
- Do not soften this by flagging them inline - they are excluded entirely
- If an event was removed because it falls outside the travel dates, note it once at
  the bottom: EXCLUDED: [name] - outside travel dates
- A clean itinerary with fewer items is better than a cluttered one with wrong items"""


def format_output(client, verified, trip_brief):
    print("\n Step 3/3 - Formatting final itinerary...")

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=FORMAT_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": f"Trip brief:\n{trip_brief}\n\nVerified content:\n{verified}\n\nFormat as clean final itinerary."
                }
            ],
            stop_sequences=None
        )

        final = response.content[0].text
        print(" Step 3 complete.")
        return final

    except Exception as e:
        print(f" Step 3 FAILED: {type(e).__name__}: {e}")
        raise


def run_chain(trip_brief: str) -> dict:
    client = get_client()
    events   = discover_events(client, trip_brief)
    draft    = generate_itinerary(client, trip_brief, events)
    verified = verify_itinerary(client, draft, trip_brief)
    final    = format_output(client, verified, trip_brief)
    return {
        "final": final,
        "events": events,
    }

