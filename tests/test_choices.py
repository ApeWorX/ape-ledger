import pytest

from ape_ledger.choices import AddressPromptChoice


@pytest.fixture(autouse=True)
def patch_device(device_factory):
    return device_factory("choices")


class TestAddressPromptChoice:
    def test_get_user_selected_account(self, mocker, hd_path, address):
        mock_prompt = mocker.patch("ape_ledger.choices.click.prompt")
        choices = AddressPromptChoice(hd_path)
        choices._choice_index = 3
        choices._index_offset = 2

        # `None` means the user hasn't selected yeet
        # And is entering other keys, possible the paging keys.
        mock_prompt_return_values = iter((None, None, None, None, address, None))

        def _side_effect(*args, **kwargs):
            return next(mock_prompt_return_values)

        mock_prompt.side_effect = _side_effect
        address, hdpath = choices.get_user_selected_account()
        assert address == address
        assert str(hdpath) == f"m/44'/60'/{choices._choice_index + choices._index_offset}'/0/0"
