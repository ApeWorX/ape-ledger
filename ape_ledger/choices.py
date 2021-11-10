from typing import Any, Optional, Tuple

import click
from ape.cli import PromptChoice
from click import Context, Parameter

from ape_ledger.client import LedgerEthereumAppClient
from ape_ledger.hdpath import HDAccountPath, HDBasePath


class AddressPromptChoice(PromptChoice):
    """
    A class for handling prompting the user for an address selection.
    """

    DEFAULT_PAGE_SIZE = 5

    def __init__(
        self,
        app: LedgerEthereumAppClient,
        index_offset: int = 0,
        page_size: int = DEFAULT_PAGE_SIZE,
    ):
        self._app = app
        self._index_offset = index_offset
        self._page_size = page_size
        self._choice_index = None

        # Must call ``_load_choices()`` to set address choices
        super().__init__([])

    @property
    def _hd_root_path(self) -> HDBasePath:
        """The base HD path of the Ethereum wallet."""
        return self._app.hd_root_path

    @property
    def _is_incremented(self) -> bool:
        """Returns ``True`` if the user has paged past the first page."""
        return (self._index_offset + self._page_size) > self._page_size

    @property
    def _prompt_message(self) -> str:
        return (
            "Please choose the address you would like to add,\n\t"
            f"or type 'n' for the next {self._page_size} entries"
        )

    def convert(
        self, value: Any, param: Optional["Parameter"], ctx: Optional["Context"]
    ) -> Optional[str]:
        """Convert the user selection to a choice or increment /decrement
        if they input ``n`` or ``p``."""
        if self._page_from_choice(value):
            # Don't select an address yet if user paged.
            return None

        address = super().convert(value, param, ctx)
        self._choice_index = self.choices.index(address)
        return address

    def get_user_selected_account(self) -> Tuple[str, HDAccountPath]:
        """Returns the selected address from the user along with the HD path.
        The user is able to page using special characters ``n`` and ``p``.
        """
        address = None
        while address is None:
            self._load_choices()
            self.print_choices()

            address = self._get_user_selection()

        account_id = self._choice_index
        return address, self._hd_root_path.get_account_path(account_id)

    def _get_user_selection(self) -> str:
        """Prompt the user for a selection."""
        prompt = self._prompt_message
        if self._is_incremented:
            prompt += f"\n\tor 'p' for the previous {self._page_size}"

        # Handle user choice from prompt, including paging.
        return click.prompt(prompt, type=self)

    def _page_from_choice(self, choice):
        choice = choice.lower()
        if choice == "n":
            self._index_offset += self._page_size
            return True
        elif choice == "p" and self._is_incremented:
            self._index_offset -= self._page_size
            return True

        return False

    def _load_choices(self):
        end_range = self._index_offset + self._page_size
        index_range = range(self._index_offset, end_range)
        self.choices = [self._get_address(i) for i in index_range]

    def _get_address(self, account_id: int) -> str:
        return str(self._app.load_account(account_id))


__all__ = ["AddressPromptChoice", "PromptChoice"]
