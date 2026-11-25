"""No paid calls: fake clock, fake sleep, and mocked transport."""
import asyncio
import unittest
from unittest.mock import patch

from forecasting_tools import GeneralLlm
from bot.request_pacing import PacedLlm, RequestPacer


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now

    async def sleep(self, delay):
        self.now += delay


class TestRequestPacing(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_calls_do_not_burst(self):
        clock = Clock()
        pacer = RequestPacer(clock=clock, sleep=clock.sleep)
        starts = []

        async def request():
            await pacer.wait()
            starts.append(clock())

        await asyncio.gather(*(request() for _ in range(40)))
        self.assertEqual(len(starts), 40)
        self.assertTrue(all(b - a >= 4 for a, b in zip(starts, starts[1:])))
        self.assertTrue(all(sum(t <= x < t + 60 for x in starts) <= 15 for t in starts))

    async def test_failed_transport_attempt_is_also_paced(self):
        clock = Clock()
        llm = PacedLlm("openrouter/openai/gpt-6-luna", allowed_tries=1)
        llm.pacer = RequestPacer(clock=clock, sleep=clock.sleep)
        starts = []

        async def transport(instance, prompt):
            starts.append(clock())
            if len(starts) == 1:
                raise RuntimeError("fake rate-limit failure")
            return "OK"

        with patch.object(GeneralLlm, "_call_litellm", transport):
            with self.assertRaises(RuntimeError):
                await llm._call_litellm("first")
            self.assertEqual(await llm._call_litellm("second"), "OK")
        self.assertEqual(starts, [100.0, 104.0])
        self.assertIs(GeneralLlm.to_llm(llm), llm)

    def test_bad_intervals_rejected(self):
        for value in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                RequestPacer(value)
