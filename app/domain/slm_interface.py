from abc import ABC, abstractmethod

class ISLM(ABC):

    @abstractmethod
    def load_model(self, model_name: str):
        pass

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str):
        pass