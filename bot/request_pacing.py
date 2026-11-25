"""Space requests before sending them, including retries and validation samples."""
import asyncio
import math
import time

from forecasting_tools import GeneralLlm


class RequestPacer:
    def __init__(self, interval_s=4.0, *, clock=time.monotonic, sleep=asyncio.sleep):
        if not math.isfinite(interval_s) or interval_s <= 0:
            raise ValueError("Request interval must be finite and positive")
        self.interval_s = interval_s
        self._clock = clock
        self._sleep = sleep
        self._lock = asyncio.Lock()
        self._next_start = 0.0

    async def wait(self):
        async with self._lock:
            delay = self._next_start - self._clock()
            if delay > 0:
                await self._sleep(delay)
            self._next_start = self._clock() + self.interval_s


class PacedLlm(GeneralLlm):
    """Pinned forecasting-tools 0.3.7 calls this hook for each API attempt."""
    def __init__(self, *args, interval_s=4.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.pacer = RequestPacer(interval_s)

    async def _call_litellm(self, prompt):
        await self.pacer.wait()
        return await super()._call_litellm(prompt)
