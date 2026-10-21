# -*- coding: utf-8 -*-
"""Коллекция наклеек: по одной за каждую пройденную тему; золотая — за 100% с первого результата."""
from curriculum import ALL_LESSONS


def collection(stats):
    done, best = stats["completed_ids"], stats["best_by_lesson"]
    out = []
    for l in ALL_LESSONS:
        r = best.get(l["id"])
        got = l["id"] in done
        gold = bool(got and r is not None and r["score_percent"] >= 100 and not r["manual"])
        out.append({"id": l["id"], "emoji": l["emoji"], "title": l["title"], "num": l.get("num"),
                    "extra": bool(l.get("is_extra")), "got": got, "gold": gold})
    return out
