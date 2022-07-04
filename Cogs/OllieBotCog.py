from abc import ABCMeta, abstractclassmethod
from typing import Any, Iterable, Optional, Union, final
from twitchio.ext import commands

## Problem is that we can only create one instance of a cog (because all instances have the same name due to the cog meta-class).
## This means that are modes and variables need to be remember for all joined channels by a single cog instance!

class OllieBotCog(commands.Cog):
    
    __slots__ = ("__modes", "__variables")
    
    def __init__(self) -> None:
        self.__modes: dict[str, bool] = self.module_modes()
    
    ##################################################
    #### Module modes
    
    @abstractclassmethod
    def module_name() -> str:
        raise NotImplementedError
    
    @abstractclassmethod
    def module_modes() -> dict[str, bool]:
        "The modes that can be changed on this module and their default state."
        raise NotImplementedError()
    
    @final
    async def modes(self) -> list[str]:
        "The modes that can be changed on this module."
        return list(self.__modes.keys())
    
    @final
    async def accepts_mode(self, mode: str) -> bool:
        "Check if a mode or modes can be changed on this module."
        return mode in self.__modes
    
    @final
    async def get_mode(self, mode: str) -> bool:
        "Get the state (whether it is enabled or disabled) of the given mode."
        return self.__modes.get(mode, False)
    
    @final
    async def set_mode(self, mode: str, enable: Optional[bool] = None) -> None:
        "Set the state (enable or disable) of the given mode in this module."
        if self.accepts_mode(mode):
            if enable is not None:
                self.__modes[mode] = enable
            else: self.__modes[mode] = not self.__modes[mode]
    
    ##################################################
    #### Module local variables
    
    async def accepts_set_vars(self) -> list[tuple[str, type]]:
        "Set the variables that the module accepts to modify its behaviour."
        return []
    
    async def accepts_get_vars(self) -> list[tuple[str, type]]:
        "Get the current values of variables that the module accepts to modify its behaviour."
        return []
    
    async def set_var(self, var_name: str, value: Any) -> None:
        "Set the value of a variable."
        return None
    
    async def get_var(self, var_name: str) -> Any:
        "Get the value of a variable."
        return None