"""
Module containing ports and adapters for final IV consumers.

Contains both the abstract interface and concrete implementation.
"""

import abc
import pickle

from volfitter.domain.datamodel import FinalIVSurface


class AbstractFinalIVConsumer(abc.ABC):
    """
    Abstract base class for final IV consumers.
    """

    @abc.abstractmethod
    def consume_final_iv_surface(self, final_iv_surface: FinalIVSurface) -> None:
        """
        Consumes a final IV surface.
        :param final_iv_surface: FinalIVSurface.
        """
        raise NotImplementedError


class PickleFinalIVConsumer(AbstractFinalIVConsumer):
    """
    Writes a FinalIVSurface to a pickle file on disc.
    """

    def __init__(self, filename: str):
        self.filename = filename

    def consume_final_iv_surface(self, final_iv_surface: FinalIVSurface) -> None:
        """
        Writes a FinalIVSurface to a pickle file on disc.
        :param final_iv_surface: FinalIVSurface.
        """
        with open(self.filename, "wb") as file:
            pickle.dump(final_iv_surface, file)
