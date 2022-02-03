import typing as tp
from collections import deque


class BrowserHistory:
    def __init__(
        self, location: tp.Any = None, max_back: int = None, max_forward: int = None
    ) -> None:
        if max_back is not None:
            max_back += 1  # +1 for storing the current location
        self._back = deque(maxlen=max_back)
        self._forward = deque(maxlen=max_forward)
        if location is not None:
            self.location = location

    @property
    def location(self) -> tp.Any:
        if self._back:
            return self._back[-1]
        raise AttributeError("Location has not been set")

    @location.setter
    def location(self, value: tp.Any) -> None:
        latest_entry = self.latest_entry()
        if not latest_entry or latest_entry.url != value.url:
            self._back.append(value)
            self._forward.clear()

    def back(self, i: int = 1) -> tp.Any:
        if i > 0:
            for _ in range(min(i, len(self._back) - 1)):
                self._forward.appendleft(self._back.pop())
        return self.location

    def forward(self, i: int = 1) -> tp.Any:
        if i > 0:
            for _ in range(i):
                self._back.append(self._forward.popleft())
        return self.location

    def go(self, i: int) -> tp.Any:
        if i < 0:
            return self.back(-i)
        if i > 0:
            return self.forward(i)
        return self.location

    def get_locations(self) -> tp.List[tp.Any]:
        result = []
        # back and current locations
        n = len(self._back) - 1
        result.extend((i - n, location) for i, location in enumerate(self._back))
        # forward locations
        result.extend((i + 1, location) for i, location in enumerate(self._forward))
        result.reverse()
        return result

    def latest_entry(self) -> tp.Optional[tp.Any]:
        try:
            return self._back[-1]
        except IndexError:
            return None
