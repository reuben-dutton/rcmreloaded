from layers.constants import (
    DEFAULT_SIZE,
)

class BaseLayer:
    
    def _create_layer(self, size: tuple[int, int] = DEFAULT_SIZE):
        raise NotImplementedError()