import time
import functools
import asyncio
from contextlib import ContextDecorator

class Timer(ContextDecorator):
    def __init__(self, name=None):
        self.name = name

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.end_time = time.perf_counter()
        self.duration = self.end_time - self.start_time
        label = f"[{self.name}]" if self.name else "Execution"
        print(f"⏱{label} took {self.duration:.4f} seconds")
        return False

def time_execution(func):
    if asyncio.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                end = time.perf_counter()
                print(f"(Async) {func.__name__} took {end - start:.4f} seconds")
        return async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                end = time.perf_counter()
                print(f"(Sync) {func.__name__} took {end - start:.4f} seconds")
        return sync_wrapper