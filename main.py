"""Appwrite Function entry point for Echo Inventory Crawler."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.runner import run_all_targets_once


def main(context):
    context.log("Echo: starting inventory check...")
    try:
        results = asyncio.run(run_all_targets_once())
        checked = sum(1 for r in results if r.get("checked"))
        skipped = len(results) - checked
        context.log(f"Echo: done — {checked} checked, {skipped} skipped (outside window)")
        return context.res.json({
            "status": "ok",
            "targets_checked": checked,
            "targets_skipped": skipped,
            "results": results,
        })
    except Exception as e:
        context.error(str(e))
        return context.res.json({"status": "error", "message": str(e)}, 500)
