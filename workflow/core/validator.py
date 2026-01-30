from abc import ABC, abstractmethod
from typing import Any, Dict, Type, Optional
import importlib

class BaseValidator(ABC):
    @abstractmethod
    def validate(self, args: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Returns True if the condition is met, False otherwise.
        """
        pass

class ValidatorRegistry:
    def __init__(self):
        self._validators: Dict[str, Type[BaseValidator]] = {}

    def register(self, name: str, validator_cls: Type[BaseValidator]):
        self._validators[name] = validator_cls

    def get(self, name: str) -> Optional[Type[BaseValidator]]:
        return self._validators.get(name)

    def load_plugin(self, name: str, class_path: str):
        """
        Dynamically loads a validator class from a string path like 'module.submodule.ClassName'
        """
        try:
            module_path, class_name = class_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            if not issubclass(cls, BaseValidator):
                raise TypeError(f"Class {class_name} must inherit from BaseValidator")
            self.register(name, cls)
        except (ImportError, AttributeError, ValueError) as e:
            raise ImportError(f"Failed to load plugin '{name}' from {class_path}: {e}")
