import asyncio


class ReadyQueuelous(asyncio.Queue):
    """An async queue that can wait for messages without popping them"""

    async def ready(self):
        while self.empty():
            getter = self._get_loop().create_future()
            self._getters.appendleft(getter)  # Make sure ready future is first
            try:
                await getter
            except:
                getter.cancel()  # Just in case getter is not done yet.
                try:
                    # Clean self._getters from canceled getters.
                    self._getters.remove(getter)
                except ValueError:
                    # The getter could be removed from self._getters by a
                    # previous put_nowait call.
                    pass
                if not self.empty() and not getter.cancelled():
                    # We were woken up by put_nowait(), but can't take
                    # the call.  Wake up the next in line.
                    self._wakeup_next(self._getters)
                raise
        self._wakeup_next(self._getters)  # Propagates readiness from put_nowait
        await asyncio.sleep(0)  # Prevent function from running synchronously

    async def put(self, item):
        """
        The following patch to `put` solves potential hanging code.

        Consider the following example:

        async with asyncio.TaskGroup() as tg:
            tg.create_task(q.ready())
            await q.put(1)
            await q.get()

        This code hangs. put() will call put_nowait because `q` is not full,
        therefore, it will wake the underlying future awaited on by ready()
        but will not yield execution back to the event loop. Afterwards, get()
        will call get_nowait because `q` is not empty and therefore will not
        yield execution back to event loop. this keeps the task group waiting.
        """
        await super().put(item)
        await asyncio.sleep(0) # forces the coroutine to yield execution.
