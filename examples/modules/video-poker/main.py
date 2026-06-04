from __future__ import annotations

import random
from collections import Counter

SUITS = ["Hearts", "Diamonds", "Clubs", "Spades"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
RANK_VALUES = {r: i for i, r in enumerate(RANKS)}

PAYOUTS = [
    ("Royal Flush", 250),
    ("Straight Flush", 50),
    ("Four of a Kind", 25),
    ("Full House", 9),
    ("Flush", 6),
    ("Straight", 4),
    ("Three of a Kind", 3),
    ("Two Pair", 2),
    ("Jacks or Better", 1),
]

_state: dict | None = None


def _make_deck() -> list[tuple[str, str]]:
    return [(r, s) for s in SUITS for r in RANKS]


def _card_str(card: tuple[str, str]) -> str:
    return f"{card[0]} of {card[1]}"


def _hand_str(hand: list[tuple[str, str]]) -> str:
    return ", ".join(
        f"  [{i+1}] {_card_str(c)}" for i, c in enumerate(hand)
    )


def _is_flush(hand: list[tuple[str, str]]) -> bool:
    return len(set(s for _, s in hand)) == 1


def _is_straight(hand: list[tuple[str, str]]) -> bool:
    vals = sorted(RANK_VALUES[r] for r, _ in hand)
    if vals == list(range(vals[0], vals[0] + 5)):
        return True
    if vals == [0, 1, 2, 3, 12]:
        return True
    return False


def _evaluate(hand: list[tuple[str, str]]) -> tuple[str, int]:
    ranks = [r for r, _ in hand]
    counts = Counter(ranks)
    freq = sorted(counts.values(), reverse=True)
    flush = _is_flush(hand)
    straight = _is_straight(hand)
    vals = sorted(RANK_VALUES[r] for r, _ in hand)

    if flush and straight:
        if vals == [8, 9, 10, 11, 12]:
            return "Royal Flush", 250
        return "Straight Flush", 50
    if freq == [4, 1]:
        return "Four of a Kind", 25
    if freq == [3, 2]:
        return "Full House", 9
    if flush:
        return "Flush", 6
    if straight:
        return "Straight", 4
    if freq == [3, 1, 1]:
        return "Three of a Kind", 3
    if freq == [2, 2, 1]:
        return "Two Pair", 2
    if freq == [2, 1, 1, 1]:
        pair_rank = [r for r, c in counts.items() if c == 2][0]
        if RANK_VALUES[pair_rank] >= RANK_VALUES["J"]:
            return "Jacks or Better", 1
    return "No Win", 0


def execute(action: str, params: dict) -> str:
    global _state

    if action == "deal":
        deck = _make_deck()
        random.shuffle(deck)
        hand = deck[:5]
        remaining = deck[5:]
        _state = {"hand": hand, "deck": remaining}

        lines = [_card_str(c) for c in hand]
        labeled = "\n".join(f"  [{i+1}] {l}" for i, l in enumerate(lines))
        return (
            f"Your hand:\n{labeled}\n\n"
            f"Choose which cards to HOLD by position (1-5).\n"
            f"Example: '1,3,5' holds cards 1, 3, and 5."
        )

    if action == "draw":
        if not _state:
            return "Error: no active hand. Use deal first."

        hold_str = params.get("hold", "")
        try:
            hold_positions = [int(x.strip()) for x in hold_str.split(",") if x.strip()]
        except ValueError:
            return "Error: hold must be comma-separated positions (1-5)"

        if any(p < 1 or p > 5 for p in hold_positions):
            return "Error: positions must be between 1 and 5"

        hand = _state["hand"]
        deck = _state["deck"]
        new_hand = []
        draw_idx = 0
        for i in range(5):
            if (i + 1) in hold_positions:
                new_hand.append(hand[i])
            else:
                new_hand.append(deck[draw_idx])
                draw_idx += 1

        _state = None

        result_name, payout = _evaluate(new_hand)
        lines = [_card_str(c) for c in new_hand]
        labeled = "\n".join(f"  [{i+1}] {l}" for i, l in enumerate(lines))

        payout_table = "\n".join(f"  {name}: {p}x" for name, p in PAYOUTS)

        return (
            f"Final hand:\n{labeled}\n\n"
            f"Result: {result_name} — Payout: {payout}x\n\n"
            f"Payout table:\n{payout_table}"
        )

    return f"Unknown action: {action}"
