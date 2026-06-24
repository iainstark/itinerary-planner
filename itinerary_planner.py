"""
Trip Itinerary Planner with Verification
=========================================
Iain Stark | June 2026

Four-step chaining workflow:
  Step 0 - Discover local events during travel dates (web search)
  Step 1 - Generate draft itinerary from trip brief + discovered events
  Step 2 - Verify date-dependent items via web search
  Step 3 - Format clean verified itinerary

Usage:
  py itinerary_planner.py
  Paste trip brief, press Enter twice.

Environment:
  JWNC managed Windows - py launcher, project venv
  Set API key: $env:ANTHROPIC_API_KEY = "your-key"
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


# ── Step 0: Discover events ───────────────────────────────────────────────────

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

Output format - return a structured list:
EVENT FOUND: [name] | [date] | [location] | [brief description] | [source]
NO EVENTS FOUND: [what you searched for]

Be thorough - this step exists specifically to catch events the user may not know about."""


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


# ── Step 1: Generate ─────────────────────────────────────────────────────────

GENERATE_SYSTEM = """You are an experienced Scottish travel planner with deep knowledge of
attractions, cafes, gardens, distilleries, walks, and seasonal access across Scotland.

Produce a detailed day-by-day draft itinerary from the trip brief and discovered events.

Rules:
- Suggest real, named places only
- For each item note: name, type, why it suits the group
- Flag anything with seasonal restrictions or limited opening hours with [CHECK]
- Keep pace realistic
- IMPORTANT: Any events found in the events discovery section must be included in the
  itinerary on their correct date - these are real confirmed events happening during the trip

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

        print(f"   stop_reason: {response.stop_reason}")
        print(f"   content blocks: {len(response.content)}")

        draft = response.content[0].text
        print(f"   draft: {len(draft)} chars")
        print(" Step 1 complete.")
        return draft

    except Exception as e:
        print(f" Step 1 FAILED: {type(e).__name__}: {e}")
        raise


# ── Step 2: Verify ───────────────────────────────────────────────────────────

VERIFY_SYSTEM = """You are a meticulous travel researcher applying Verification Protocol 2.

Take a draft itinerary and verify every date-dependent item against the actual travel
dates using web search.

For EVERY named venue, attraction, walk, cafe, or activity:
1. Search for current opening hours, access restrictions, seasonal closures
2. Check specifically against the travel dates provided
3. Mark each item:
   CHECK_PASS: [venue] - confirmed open/accessible on [dates]
   CHECK_FAIL: [venue] - [reason: closed / restricted / unverified]

Critical checks:
- Royal estates (Balmoral etc) - check royal residence calendar
- NTS/Historic Environment Scotland properties - check seasonal hours
- Distilleries - check tour booking requirements and opening days
- Cafes/restaurants - check current trading status
- Any item marked [CHECK] in the draft

Output: verification summary first, then full itinerary with status markers inline"""


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
                print(" Step 2: no text block found")
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
        print(" Falling back to unverified draft")
        return draft


# ── Step 3: Format ───────────────────────────────────────────────────────────

FORMAT_SYSTEM = """You are a travel itinerary formatter.

Take a verified itinerary and produce a clean, readable final version.

Format rules:
- Clear day-by-day structure with dates
- Each item: time suggestion, venue name, brief description, status (CONFIRMED / CHECK BEFORE VISITING)
- CHECK BEFORE VISITING items include a one-line note on what to confirm
- Events discovered from Step 0 should be clearly highlighted as KEY EVENT
- End with a Before You Go checklist of all items needing manual confirmation
- Friendly, practical tone"""


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


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  TRIP ITINERARY PLANNER - Verification Protocol 2")
    print("=" * 60)
    print("\nPaste your trip brief. Press Enter twice when done.\n")

    lines = []
    while True:
        line = input()
        if line == "" and lines and lines[-1] == "":
            break
        lines.append(line)

    trip_brief = "\n".join(lines).strip()

    if not trip_brief:
        print("No brief entered. Exiting.")
        sys.exit(0)

    print(f"\n Brief received: {len(trip_brief)} chars")
    print("=" * 60)

    client = get_client()

    # Four-step chain
    events   = discover_events(client, trip_brief)
    draft    = generate_itinerary(client, trip_brief, events)
    verified = verify_itinerary(client, draft, trip_brief)
    final    = format_output(client, verified, trip_brief)

    print("\n" + "=" * 60)
    print("  YOUR VERIFIED ITINERARY")
    print("=" * 60)
    print(final)

    output_file = "itinerary_output.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("TRIP ITINERARY\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"BRIEF:\n{trip_brief}\n\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"EVENTS DISCOVERED:\n{events}\n\n")
        f.write("=" * 60 + "\n\n")
        f.write(final)

    print(f"\n Saved to: {output_file}")
    print("Done.")


if __name__ == "__main__":
    main()
