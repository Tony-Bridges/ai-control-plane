#!/usr/bin/env python
"""Simple load-testing script for the /v1/ai/process endpoint.

Usage: python scripts/load_test.py --url http://localhost:8080 --requests 100 --concurrency 10
"""
import argparse
import asyncio
import time
import statistics
import httpx


SAMPLE_PROMPTS = [
    "Summarize the Q3 financial report.",
    "What is the leave policy for engineering staff?",
    "Please help me draft an email to a customer.",
]


async def send_request(client: httpx.AsyncClient, url: str, index: int) -> float:
    payload = {
        "user_id": f"load-test-user-{index % 10}",
        "department": "engineering",
        "prompt": SAMPLE_PROMPTS[index % len(SAMPLE_PROMPTS)],
    }
    start = time.time()
    try:
        resp = await client.post(f"{url}/v1/ai/process", json=payload, timeout=30.0)
        resp.raise_for_status()
    except Exception as e:
        print(f"Request {index} failed: {e}")
    return (time.time() - start) * 1000


async def run_load_test(url: str, total_requests: int, concurrency: int):
    semaphore = asyncio.Semaphore(concurrency)
    durations = []

    async def worker(i):
        async with semaphore:
            async with httpx.AsyncClient() as client:
                durations.append(await send_request(client, url, i))

    await asyncio.gather(*(worker(i) for i in range(total_requests)))

    print(f"\nCompleted {total_requests} requests with concurrency {concurrency}")
    print(f"  p50: {statistics.median(durations):.2f}ms")
    print(f"  avg: {statistics.mean(durations):.2f}ms")
    print(f"  max: {max(durations):.2f}ms")
    print(f"  min: {min(durations):.2f}ms")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8080")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    args = parser.parse_args()

    asyncio.run(run_load_test(args.url, args.requests, args.concurrency))
